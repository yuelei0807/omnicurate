# Data Quality Report

## Summary

- **Total exceptions:** 17
- **Unique rules triggered:** 12

### Severity breakdown

| Severity | Count |
|----------|------:|
| High | 8 |
| Medium | 9 |

## By Rule

| Rule | Description | Severity | Violations |
|------|-------------|----------|----------:|
| DQ001 | customer_id must be unique after duplicate resolution | High | 1 |
| DQ002 | email should be present and syntactically valid when available | Medium | 1 |
| DQ003 | country and state must be standardized | Medium | 6 |
| DQ004 | order_id must be unique | High | 1 |
| DQ005 | customer_id must exist in customers | High | 1 |
| DQ006 | product_id must exist in products | High | 1 |
| DQ007 | completed orders must have positive quantity | High | 1 |
| DQ008 | order_total should equal quantity times product unit_price | High | 1 |
| DQ009 | payment order_id must exist in orders | High | 1 |
| DQ010 | settled payment amount should equal completed order total | High | 1 |
| DQ011 | created_ts must parse to a valid timestamp | Medium | 1 |
| DQ012 | customer_id should exist in customers | Medium | 1 |

## Sample records

Up to five example rows per rule (most recent first).

### DQ001

| Record key | Severity | Issue |
|------------|----------|-------|
| C006 | High | Duplicate customer_id=C006; this row (email=mason.d@example.com) was dropped in favour of the canonical first occurre... |

### DQ002

| Record key | Severity | Issue |
|------------|----------|-------|
| C004 | Medium | customer_id=C004: email is missing. |

### DQ003

| Record key | Severity | Issue |
|------------|----------|-------|
| C002 | Medium | customer_id=C002: country 'US' standardized to 'USA'; state 'Illinois' standardized to 'IL'. |
| C003 | Medium | customer_id=C003: country 'United States' standardized to 'USA'. |
| C006 | Medium | customer_id=C006: country 'US' standardized to 'USA'; state 'New York' standardized to 'NY'. |
| C008 | Medium | customer_id=C008: state 'Texas' standardized to 'TX'. |
| C011 | Medium | customer_id=C011: country 'United States' standardized to 'USA'. |

### DQ004

| Record key | Severity | Issue |
|------------|----------|-------|
| O1018 | High | Duplicate order_id=O1018; identical row was dropped (no information lost). |

### DQ005

| Record key | Severity | Issue |
|------------|----------|-------|
| O1019 | High | order_id=O1019: customer_id 'C999' not found in customers. |

### DQ006

| Record key | Severity | Issue |
|------------|----------|-------|
| O1020 | High | order_id=O1020: product_id 'P999' not found in products. |

### DQ007

| Record key | Severity | Issue |
|------------|----------|-------|
| O1030 | High | order_id=O1030: completed-order quantity -1 is not positive. |

### DQ008

| Record key | Severity | Issue |
|------------|----------|-------|
| O1021 | High | order_id=O1021: order_total=50.00 vs quantity*unit_price=44.00 (diff=6.00). |

### DQ009

| Record key | Severity | Issue |
|------------|----------|-------|
| PMT029 | High | Orphan payment: order_id=O9999 not found in orders (payment_id=PMT029). |

### DQ010

| Record key | Severity | Issue |
|------------|----------|-------|
| PMT021 | High | payment_id=PMT021: settled payment 44.00 != completed order total 50.00 (diff=6.00). |

### DQ011

| Record key | Severity | Issue |
|------------|----------|-------|
| T010 | Medium | ticket_id=T010: created_ts failed to parse: 'bad_timestamp'. |

### DQ012

| Record key | Severity | Issue |
|------------|----------|-------|
| T005 | Medium | ticket_id=T005: customer_id 'C999' not found in customers. |
