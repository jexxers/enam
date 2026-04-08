package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthEndpoint(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	w := httptest.NewRecorder()

	healthHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	var resp map[string]string
	json.NewDecoder(w.Body).Decode(&resp)
	if resp["status"] != "ok" {
		t.Fatalf("expected status ok, got %s", resp["status"])
	}
}

func TestCategoriesEndpoint(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/api/categories", nil)
	w := httptest.NewRecorder()

	categoriesHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	var resp map[string][]string
	json.NewDecoder(w.Body).Decode(&resp)
	if len(resp["categories"]) != 7 {
		t.Fatalf("expected 7 categories, got %d", len(resp["categories"]))
	}
}

func postExpense(t *testing.T, exp ExpenseRequest) ValidationResponse {
	t.Helper()
	body, _ := json.Marshal(exp)
	req := httptest.NewRequest(http.MethodPost, "/api/expenses/validate", bytes.NewReader(body))
	w := httptest.NewRecorder()

	validateHandler(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	var resp ValidationResponse
	json.NewDecoder(w.Body).Decode(&resp)
	return resp
}

func TestValidExpense(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:             "2025-03-01",
		Description:      "Office chair",
		Amount:           249.99,
		Category:         "equipment",
		InvoiceReference: "INV-2025-001",
	})
	if resp.Status != "approved" {
		t.Fatalf("expected approved, got %s: %v", resp.Status, resp.Reasons)
	}
}

func TestUnder50NoInvoiceIsValid(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:        "2025-03-03",
		Description: "Team lunch",
		Amount:      42.50,
		Category:    "meals",
	})
	if resp.Status != "approved" {
		t.Fatalf("expected approved, got %s: %v", resp.Status, resp.Reasons)
	}
}

func TestNegativeAmount(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:             "2025-03-15",
		Description:      "Keyboard",
		Amount:           -45.00,
		Category:         "equipment",
		InvoiceReference: "INV-001",
	})
	if resp.Status != "rejected" {
		t.Fatal("expected rejected for negative amount")
	}
	assertContainsReason(t, resp.Reasons, "amount must be a positive number")
}

func TestInvalidDate(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:        "03/15/2025",
		Description: "Lunch",
		Amount:      20.00,
		Category:    "meals",
	})
	if resp.Status != "rejected" {
		t.Fatal("expected rejected for invalid date format")
	}
	assertContainsReason(t, resp.Reasons, "date is invalid or missing")
}

func TestInvalidCategory(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:             "2025-03-08",
		Description:      "Conference",
		Amount:           800.00,
		Category:         "conferences",
		InvoiceReference: "INV-001",
	})
	if resp.Status != "rejected" {
		t.Fatal("expected rejected for invalid category")
	}
	assertContainsReason(t, resp.Reasons, "invalid category")
}

func TestMissingDescription(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:             "2025-03-19",
		Description:      "",
		Amount:           75.00,
		Category:         "office_supplies",
		InvoiceReference: "INV-001",
	})
	if resp.Status != "rejected" {
		t.Fatal("expected rejected for missing description")
	}
	assertContainsReason(t, resp.Reasons, "description is required")
}

func TestMissingInvoiceOver50(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:        "2025-03-04",
		Description: "Standing desk",
		Amount:      599.99,
		Category:    "equipment",
	})
	if resp.Status != "rejected" {
		t.Fatal("expected rejected for missing invoice on amount > $50")
	}
	assertContainsReason(t, resp.Reasons, "invoice_reference is required")
}

func TestMultipleValidationErrors(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:        "invalid",
		Description: "",
		Amount:      -10,
		Category:    "bogus",
	})
	if resp.Status != "rejected" {
		t.Fatal("expected rejected")
	}
	if len(resp.Reasons) < 3 {
		t.Fatalf("expected at least 3 reasons, got %d: %v", len(resp.Reasons), resp.Reasons)
	}
}

func TestExactly50NoInvoiceIsValid(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:        "2025-03-01",
		Description: "Office supplies",
		Amount:      50.00,
		Category:    "office_supplies",
	})
	if resp.Status != "approved" {
		t.Fatalf("expected approved for exactly $50 without invoice, got %s: %v", resp.Status, resp.Reasons)
	}
}

func TestJustOver50RequiresInvoice(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:        "2025-03-01",
		Description: "Office supplies",
		Amount:      50.01,
		Category:    "office_supplies",
	})
	if resp.Status != "rejected" {
		t.Fatal("expected rejected for $50.01 without invoice")
	}
	assertContainsReason(t, resp.Reasons, "invoice_reference is required")
}

func TestZeroAmount(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:        "2025-03-01",
		Description: "Free item",
		Amount:      0,
		Category:    "other",
	})
	if resp.Status != "rejected" {
		t.Fatal("expected rejected for zero amount")
	}
	assertContainsReason(t, resp.Reasons, "amount must be a positive number")
}

func TestCategoryIsCaseInsensitive(t *testing.T) {
	resp := postExpense(t, ExpenseRequest{
		Date:             "2025-03-01",
		Description:      "Flight",
		Amount:           200.00,
		Category:         "Travel",
		InvoiceReference: "INV-001",
	})
	if resp.Status != "approved" {
		t.Fatalf("expected approved for mixed-case category, got %s: %v", resp.Status, resp.Reasons)
	}
}

func TestExpenseEchoedBack(t *testing.T) {
	exp := ExpenseRequest{
		Date:             "2025-03-01",
		Description:      "Test expense",
		Amount:           100.00,
		Category:         "other",
		InvoiceReference: "INV-TEST",
	}
	resp := postExpense(t, exp)
	if resp.Expense.Description != exp.Description {
		t.Fatalf("expected expense echoed back, got %+v", resp.Expense)
	}
	if resp.Expense.Amount != exp.Amount {
		t.Fatalf("expected amount %f, got %f", exp.Amount, resp.Expense.Amount)
	}
}

func TestEmptyBody(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/api/expenses/validate", bytes.NewReader([]byte("{}")))
	w := httptest.NewRecorder()
	validateHandler(w, req)

	var resp ValidationResponse
	json.NewDecoder(w.Body).Decode(&resp)
	if resp.Status != "rejected" {
		t.Fatal("expected rejected for empty body")
	}
	if len(resp.Reasons) < 2 {
		t.Fatalf("expected multiple reasons for empty body, got %d: %v", len(resp.Reasons), resp.Reasons)
	}
}

func TestAllCategories(t *testing.T) {
	for _, cat := range allowedCategories {
		resp := postExpense(t, ExpenseRequest{
			Date:        "2025-03-01",
			Description: "Test " + cat,
			Amount:      10.00,
			Category:    cat,
		})
		if resp.Status != "approved" {
			t.Fatalf("expected approved for category %q, got %s: %v", cat, resp.Status, resp.Reasons)
		}
	}
}

func TestMethodNotAllowed(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/api/health", nil)
	w := httptest.NewRecorder()
	healthHandler(w, req)
	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestInvalidJSON(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/api/expenses/validate", bytes.NewReader([]byte("not json")))
	w := httptest.NewRecorder()
	validateHandler(w, req)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func assertContainsReason(t *testing.T, reasons []string, substr string) {
	t.Helper()
	for _, r := range reasons {
		if contains(r, substr) {
			return
		}
	}
	t.Fatalf("expected reason containing %q, got %v", substr, reasons)
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && searchString(s, substr)
}

func searchString(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
