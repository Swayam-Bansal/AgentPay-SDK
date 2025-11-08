## AgentPay SDK – High-Level Description for the Coding Agent

We are building a standalone repository called **`agentpay-sdk`**.

This repo is **not** the UI or the governance system.
It is a **payment brain and ledger for agents** that any project can import and use.

At a high level, this SDK must provide:

1. An **abstract payment model** (agents, wallets, policies, payment intents, transfers, escrow, streams).
2. A **built-in internal ledger** using a “credits” currency as the **default rail**.
3. A **rail adapter interface** to integrate external payment rails in the future (Stripe, AP2-style systems, Agent Pay, etc.).
4. A **high-level Agent API** so callers can say things like “pay this agent”, “lock funds in escrow”, “start a streaming payment” without worrying about how it’s implemented.
5. An **optional HTTP layer** (small REST API) so non-Python / non-TS projects can still talk to the SDK over HTTP.

Below is what each piece means in detail.

---

## 1. Abstract Payment Model

The SDK defines the **core objects and rules** of agent-to-agent payments. It should *not* be tied to any specific LLM, UI, or product.

Core concepts:

1. **Agent**

   * Logical identity that can **own money** and **sign payment intents**.
   * Each agent has:

     * A unique ID.
     * A wallet.
     * A policy controlling how it can spend.
     * Optional metadata (e.g., display name, role, external references).

2. **Wallet**

   * Every agent has exactly one wallet in the internal system.
   * Holds:

     * `balance` (available credits).
     * `hold` (credits reserved for escrow, pending payouts, etc.).
   * All amounts are represented as **integers in smallest unit (e.g., cents)**, never as floats.

3. **Policy**
   Per-agent rules that restrict how the agent can spend. Examples:

   * `max_per_transaction` (upper bound on a single payment).
   * `daily_spend_cap` (max total outgoing spend per UTC day).
   * `require_human_approval_over_x` (threshold beyond which a human must approve).
   * `allowlist` (which agents this agent is allowed to pay).
   * `paused` (global kill-switch: if true, this agent cannot spend).

4. **PaymentIntent**

   * A **request** to move value from one agent to another.
   * Contains:

     * `from_agent`, `to_agent`
     * `amount`
     * `status` (e.g., `REQUIRES_CONFIRMATION`, `COMPLETED`, `FAILED_POLICY`, `FAILED_FUNDS`, `CANCELLED`)
     * Optional memo / metadata.
     * An idempotency key and (optionally) a cryptographic signature.
   * Confirming a PaymentIntent must:

     * Enforce policies.
     * Ensure sufficient funds.
     * Update the ledger and wallets atomically.

5. **Transfer / LedgerEntry**

   * Every movement of value is represented in a **double-entry ledger**.
   * Each transaction is recorded as at least **two ledger entries**:

     * One negative (debit) from payer.
     * One positive (credit) to payee.
   * Ledger entries include:

     * `agent_id`
     * `delta_amount` (positive or negative)
     * Type (`PAYMENT`, `ESCROW_LOCK`, `ESCROW_RELEASE`, `STREAM_TICK`, `TOP_UP`, etc.)
     * Reference (which PaymentIntent / Escrow / Stream they belong to)
     * `balance_after` for that agent.

6. **Escrow**

   * A mechanism where payer locks funds that can later be released or cancelled.
   * When created:

     * Funds move from payer’s `balance` into payer’s `hold`.
   * When released:

     * Funds move from payer’s `hold` into payee’s `balance`.
   * When cancelled:

     * Funds move from payer’s `hold` back to payer’s `balance`.

7. **Stream (Streaming Payment)**

   * Represents a payment over time, usually at a fixed rate (e.g., X cents per minute).
   * Has:

     * `from_agent`, `to_agent`
     * `rate_per_interval` (e.g., per minute)
     * `cap` (max total to pay)
     * `spent` (how much has been paid so far)
     * `status` (`ACTIVE`, `STOPPED`).
   * The SDK supports **ticks**: discrete chunks of payment calculated from elapsed time or units of work, respecting caps and policies.

These abstractions must be **rail-agnostic**: they don’t care whether money ultimately comes from Stripe, a bank, or a simulated balance. They only care about internal credits and consistency.

---

## 2. Internal Ledger (Default Rail)

The SDK includes its own **internal rail**. Think of it as a “credits” system:

* This is the **default and guaranteed** implementation for moving value between agents.
* It is always available, even if no external rails are configured.
* It is responsible for:

  * Maintaining each agent’s `balance` and `hold`.
  * Enforcing **double-entry accounting** and invariants:

    * No negative balances.
    * Sum of all deltas across all agents for a given transfer equals **zero** (value conservation).
  * Handling:

    * Confirmed payments.
    * Escrow lock/release/cancel.
    * Streaming payments (ticks).
    * Top-ups and adjustments in “credits”.

This “internal credits” model lets us:

* Run everything in **test/sandbox mode** without real money.
* Provide deterministic, reproducible behavior.
* Let external rails be layered on top later.

The internal ledger is **the source of truth** for the SDK. Even when external rails are used, their results are mirrored here as ledger entries.

---

## 3. Rail Adapter Interface (External Rails)

We want this SDK to be “**infra for all rails**”.

That means we define a **generic rail adapter interface** that external payment systems can implement. Examples of rails we might plug in:

* Stripe or Stripe Agent Toolkit.
* AP2-like agent payment protocols.
* Mastercard Agent Pay.
* Bank transfer or crypto rails.

The rail adapter interface must define *what the SDK expects from any rail*, not how it’s implemented.

High-level responsibilities of a rail adapter:

1. **Top-ups / Funding**

   * Ability to convert external money into internal credits.
   * Example operations:

     * Create a top-up request.
     * Confirm that real funds arrived.
     * Notify the SDK so it can credit the internal wallet.

2. **Withdrawals / Cash-out**

   * Ability to convert internal credits into real money for the agent.
   * Example operations:

     * Withdraw a certain amount to a bank/Stripe account.
     * Record the result in the internal ledger.

3. **Direct Payments (optional, future)**

   * For some rails, we may want to run **real-time payments** directly on them.
   * Rail adapter would then:

     * Accept a PaymentIntent.
     * Initiate a real payment via the external rail.
     * Update our internal ledger when done (success or failure).

4. **Status & Reconciliation (future)**

   * Ability to check the status of external transactions.
   * Ability to reconcile internal ledger with an external statement.

For the hackathon:

* The **internal credits rail** will be fully implemented.
* External rails can be represented as **adapter stubs** or simple placeholders with clear comments and future work notes.
* The key is to show the **interface** and how future adapters would plug in, even if we only use internal credits during the demo.

---

## 4. High-Level Agent API (What Callers Use)

The SDK exposes a **simple, high-level API** to applications.

An app using this SDK **does not deal with ledger entries directly**. Instead, it calls semantic operations like:

1. **Agent & Wallet Management**

   * Create/register a new agent and its wallet.
   * Set or update policy for an agent.
   * Get current wallet balances (balance + hold).
   * Fetch recent transactions (ledger entries) for display.

2. **One-off Payments**

   * Create a payment intent between agents.
   * Confirm (or cancel) the payment intent.
   * Automatically run policy checks (caps, allowlists, paused).
   * Return a structured result:

     * Success/failure.
     * Codes for policy violations, insufficient funds, etc.
     * IDs and references to ledger entries.

3. **Escrow**

   * Create/lock an escrow (payer → hold).
   * Release escrow (hold → payee).
   * Cancel escrow (hold → payer).
   * Return escrow status and related ledger history.

4. **Streaming Payments**

   * Start a stream with a rate and cap.
   * Tick the stream (time-based or unit-based).
   * Stop a stream.
   * Enforce:

     * Caps.
     * Policies.
     * Sufficient funds at each tick.

5. **Top-ups / Test Credits**

   * Methods to add test credits to wallets in sandbox mode.
   * (In the future) methods to initiate top-ups via external rails.

**Important:**
The high-level API must handle:

* **Idempotency**: allow the caller to re-send the same request safely using an idempotency key.
* **Predictable errors**: the SDK should always return clear error codes and messages (e.g., `POLICY_NOT_ALLOWLISTED`, `INSUFFICIENT_FUNDS`, `DAILY_CAP_EXCEEDED`, `AGENT_PAUSED`), so the calling app can display meaningful messages.

This is what other projects will interact with. They shouldn’t need to know how ledger entries are structured internally.

---

## 5. Optional HTTP Layer (REST Interface)

In addition to being usable as a code library, `agentpay-sdk` should optionally provide a **thin HTTP API** so that:

* Other languages and services can use it over HTTP.
* Projects can run AgentPay as a small sidecar or microservice.

This HTTP layer:

* Lives inside the same repo, but is a **thin wrapper** around the SDK’s high-level API.
* Exposes endpoints for:

  * Agent registration and policy management.
  * Balance and transaction queries.
  * Payments, escrows, streams, and test top-ups.
* Handles:

  * Authentication (e.g., API keys).
  * Idempotency headers.
  * Serialization of requests and responses into JSON.

For the hackathon, the HTTP layer can be minimal (enough to demo from other processes or tools), but the design should anticipate:

* Separate deployment.
* Simple scaling.
* Compatibility with any client that can make HTTP requests.

---

## Summary

So, in short, the `agentpay-sdk` repo is:

* A **core payment engine for agents**, with:

  * A clean abstract model of agents, wallets, policies, payment intents, escrow, and streams.
  * A robust, rail-agnostic **internal credits ledger** as the default way to move value.
  * A **rail adapter interface** designed so that in the future, Stripe, AP2, and other systems can plug in seamlessly.
  * A **high-level Agent API** that apps (like Quorum) can use without thinking about low-level money mechanics.
  * An **optional HTTP layer** so any language or service can integrate over REST.