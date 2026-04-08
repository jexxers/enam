package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
)

var allowedCategories = []string{
	"travel",
	"meals",
	"office_supplies",
	"software",
	"equipment",
	"training",
	"other",
}

type ExpenseRequest struct {
	Date             string  `json:"date"`
	Description      string  `json:"description"`
	Amount           float64 `json:"amount"`
	Category         string  `json:"category"`
	InvoiceReference string  `json:"invoice_reference"`
}

type ValidationResponse struct {
	Expense ExpenseRequest `json:"expense"`
	Status  string         `json:"status"`
	Reasons []string       `json:"reasons"`
}

func validateExpense(exp ExpenseRequest) (string, []string) {
	var reasons []string

	// 1. Amount must be positive
	if exp.Amount <= 0 {
		reasons = append(reasons, "amount must be a positive number")
	}

	// 2. Date must be valid YYYY-MM-DD
	parsedDate, err := time.Parse("2006-01-02", exp.Date)
	if err != nil {
		reasons = append(reasons, "date is invalid or missing; expected format YYYY-MM-DD")
	} else {
		// 3. Date must not be in the future
		if parsedDate.After(time.Now()) {
			reasons = append(reasons, "date cannot be in the future")
		}
	}

	// 4. Category must be from allowed list
	categoryValid := false
	for _, c := range allowedCategories {
		if strings.ToLower(exp.Category) == c {
			categoryValid = true
			break
		}
	}
	if !categoryValid {
		reasons = append(reasons, fmt.Sprintf(
			"invalid category '%s'; must be one of: %s",
			exp.Category, strings.Join(allowedCategories, ", "),
		))
	}

	// 5. Description must be non-empty
	if strings.TrimSpace(exp.Description) == "" {
		reasons = append(reasons, "description is required")
	}

	// 6. Invoice reference required for amounts over $50
	if exp.Amount > 50 && strings.TrimSpace(exp.InvoiceReference) == "" {
		reasons = append(reasons, "invoice_reference is required for amounts over $50.00")
	}

	if len(reasons) > 0 {
		return "rejected", reasons
	}
	return "approved", reasons
}

func corsMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}

		next(w, r)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func categoriesHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string][]string{"categories": allowedCategories})
}

func validateHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var exp ExpenseRequest
	if err := json.NewDecoder(r.Body).Decode(&exp); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{
			"error": "invalid JSON: " + err.Error(),
		})
		return
	}

	status, reasons := validateExpense(exp)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ValidationResponse{
		Expense: exp,
		Status:  status,
		Reasons: reasons,
	})

	log.Printf("POST /api/expenses/validate | %s | %s | $%.2f | %s",
		exp.Date, exp.Category, exp.Amount, status)
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	http.HandleFunc("/api/health", corsMiddleware(healthHandler))
	http.HandleFunc("/api/categories", corsMiddleware(categoriesHandler))
	http.HandleFunc("/api/expenses/validate", corsMiddleware(validateHandler))

	fmt.Printf("Expense Validator API Server\n")
	fmt.Printf("============================\n")
	fmt.Printf("Listening on port %s\n\n", port)
	fmt.Printf("Endpoints:\n")
	fmt.Printf("  GET  /api/health              - Health check\n")
	fmt.Printf("  GET  /api/categories           - List allowed categories\n")
	fmt.Printf("  POST /api/expenses/validate    - Validate an expense\n\n")

	log.Fatal(http.ListenAndServe(":"+port, nil))
}
