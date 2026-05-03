package main

import (
	"log"
	"net/http"
	"os"

	"vant2/services/api/internal/httpapi"
)

func main() {
	h := httpapi.NewRouter()
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	addr := ":" + port
	log.Printf("api server listening on %s", addr)
	if err := http.ListenAndServe(addr, h); err != nil {
		log.Fatal(err)
	}
}
