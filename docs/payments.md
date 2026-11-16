# Payment preparation

The backend stores QRIS payment **drafts**. It does not create QR codes, charge users, accept payment notifications, or mark a payment paid. A real QRIS integration requires a merchant account with a Bank Indonesia-authorized payment service provider. Verify the provider's API, fees, settlement terms, and merchant eligibility before enabling it.

[Hyperswitch](https://github.com/juspay/hyperswitch) is an Apache-2.0 open source payment orchestration platform that can be self-hosted. It is a candidate to evaluate if multiple payment providers are needed; its QRIS support with a specific Indonesian provider has not been established here. For a single provider, a direct adapter may be simpler. Either approach still needs a QRIS provider and merchant account.

## Draft API

Authenticated members and admins can create a draft with `POST /api/v1/payments`. Supply a unique, client-generated `Idempotency-Key` header (1–128 visible ASCII characters) and JSON:

```json
{"reference":"order-123", "amount":10000, "currency":"IDR"}
```

`amount` is an integer number of rupiah between 1 and 10,000,000. `currency` defaults to IDR. The first request returns 201 with a draft; a retry by the same user with the same key and identical normalized fields returns 200 with the same draft. Reusing that key with different details returns 409. Keys are scoped to the authenticated user and kept for the lifetime of the record. `GET /api/v1/payments/{id}` returns only the caller's draft. A unique PostgreSQL index ensures concurrent requests cannot create more than one draft per user and key.

The amount and reference currently come from the client, and no order or price is verified. **Do not use a draft as authority to charge money or grant an entitlement.** Connect payment creation to a server-owned order, calculate its price on the server, and confirm its ownership before enabling a provider.

## Provider implementation checklist

Once a provider is chosen, implement its documented API in a separate adapter. Persist a unique provider request reference and use the provider's supported idempotency mechanism. Design recovery for timeouts and crashes where the provider may have accepted a request before the backend saved its response; reconcile with the provider rather than issuing a new charge blindly.

Implement the provider-specific webhook only after its signing and verification scheme is known. Verify raw payloads according to that scheme, confirm merchant account, reference, amount, currency and provider transaction ID against the saved order, record unique provider event IDs transactionally, and define allowed state transitions. Handle duplicate and out-of-order events without granting an entitlement twice. Reconcile missed notifications against the provider and retain an audit trail. Test these paths with the provider's sandbox and real PostgreSQL before accepting money.

See [Bank Indonesia's QRIS information](https://www.bi.go.id/id/fungsi-utama/sistem-pembayaran/ritel/kanal-layanan/qris/default.aspx) for authorized providers and transaction limits. An open source backend can integrate QRIS, but does not itself provide merchant settlement or guarantee free transactions.
