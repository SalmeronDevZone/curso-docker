// Servidor web mínimo en Go. Lo usamos para ver el efecto de un build
// multi-etapa: Go compila a UN binario estático que no necesita nada más.
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	contenedor, _ := os.Hostname()

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "¡Hola desde Go! Contenedor: %s\n", contenedor)
	})

	log.Println("Escuchando en el puerto 8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
