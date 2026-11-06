package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

type Peer struct {
	Conn *websocket.Conn
	Role string // "parent" or "child"
	Mu   sync.Mutex
}

type Hub struct {
	Rooms map[string]map[string]*Peer // roomID (childId) -> role -> Peer
	Mu    sync.RWMutex
}

var hub = Hub{Rooms: make(map[string]map[string]*Peer)}

type SignalMessage struct {
	SignalID string          `json:"signalId"`
	RoomID   string          `json:"roomId"`
	Target   string          `json:"target"` // "parent" or "child"
	Payload  json.RawMessage `json:"payload"`
}

func (p *Peer) SafeWriteJSON(v interface{}) error {
	p.Mu.Lock()
	defer p.Mu.Unlock()
	p.Conn.SetWriteDeadline(time.Now().Add(5 * time.Second))
	return p.Conn.WriteJSON(v)
}

func wsHandler(w http.ResponseWriter, r *http.Request) {
	roomID := r.URL.Query().Get("roomId")
	role := r.URL.Query().Get("role")
	if roomID == "" || (role != "parent" && role != "child") {
		http.Error(w, "Missing roomId or valid role", http.StatusBadRequest)
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("[wsHandler] Upgrade error: %v", err)
		return
	}

	peer := &Peer{Conn: conn, Role: role}

	// Register Peer in Room
	hub.Mu.Lock()
	if hub.Rooms[roomID] == nil {
		hub.Rooms[roomID] = make(map[string]*Peer)
	}
	if oldPeer, exists := hub.Rooms[roomID][role]; exists {
		oldPeer.Conn.Close()
	}
	hub.Rooms[roomID][role] = peer
	log.Printf("[Connect] Room: %s, Role: %s (Active peers in room: %d)", roomID, role, len(hub.Rooms[roomID]))
	hub.Mu.Unlock()

	defer func() {
		hub.Mu.Lock()
		if hub.Rooms[roomID] != nil && hub.Rooms[roomID][role] == peer {
			delete(hub.Rooms[roomID], role)
			log.Printf("[Disconnect] Room: %s, Role: %s (Remaining: %d)", roomID, role, len(hub.Rooms[roomID]))
			if len(hub.Rooms[roomID]) == 0 {
				delete(hub.Rooms, roomID)
			}
		}
		hub.Mu.Unlock()
		conn.Close()
	}()

	// 20-Second Read Deadline + Pong Handler
	conn.SetReadLimit(65536)
	conn.SetReadDeadline(time.Now().Add(45 * time.Second))
	conn.SetPongHandler(func(string) error {
		conn.SetReadDeadline(time.Now().Add(45 * time.Second))
		return nil
	})

	// Background 20s Ping Ticker (Jio/Airtel CGNAT Drop Prevention)
	go func() {
		ticker := time.NewTicker(20 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			peer.Mu.Lock()
			conn.SetWriteDeadline(time.Now().Add(5 * time.Second))
			err := conn.WriteMessage(websocket.PingMessage, nil)
			peer.Mu.Unlock()
			if err != nil {
				return
			}
		}
	}()

	// Read & Route Signals
	for {
		var msg SignalMessage
		if err := conn.ReadJSON(&msg); err != nil {
			break
		}

		hub.Mu.RLock()
		targetPeer := hub.Rooms[roomID][msg.Target]
		hub.Mu.RUnlock()

		// Critical Fix 1: Instant Fallback Trigger if target peer is offline in the room
		if targetPeer == nil {
			_ = peer.SafeWriteJSON(map[string]interface{}{
				"type":     "fallback_required",
				"signalId": msg.SignalID,
				"reason":   "peer_offline",
			})
			continue
		}

		// Forward payload to target peer
		if err := targetPeer.SafeWriteJSON(msg); err != nil {
			_ = peer.SafeWriteJSON(map[string]interface{}{
				"type":     "fallback_required",
				"signalId": msg.SignalID,
				"reason":   "send_failed",
			})
		} else {
			// Delivery Confirmation (ACK) to sender
			_ = peer.SafeWriteJSON(map[string]interface{}{
				"type":     "ack",
				"signalId": msg.SignalID,
			})
		}
	}
}

func main() {
	http.HandleFunc("/ws", wsHandler)
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("OK"))
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "7860"
	}
	log.Printf("GoPush server listening on :%s", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

