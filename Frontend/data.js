// Mock data for the demo. Later, replace with fetch() calls to the FastAPI backend.
window.HEALTHSYNC_DATA = {
  baseTrace: [
    { who: "Sentinel", action: "ran 72-hour simulation", detail: "Threshold exceeded for Drug B" },
    { who: "Sentinel", action: "proposed dose adjustment", detail: "Re-simulated, within safe range" },
    { who: "PA Resolver", action: "matched payer policy", detail: "Source: policy document, section 3" },
    { who: "System", action: "paused for clinician approval" }
  ],
  phases: {
    awaiting: {
      header: { tone: "warn", text: "Awaiting clinician approval" },
      stages: [
        { label: "1 · Clinical Sentinel", tone: "warn", text: "Warning · dose adjusted" },
        { label: "2 · PA Resolver", tone: "info", text: "Draft ready" },
        { label: "3 · Supply Agent", tone: "idle", text: "Queued" }
      ],
      paSteps: [
        ["Gathering evidence", "done"],
        ["Package compiled", "done"],
        ["Awaiting approval to submit", "current"],
        ["Payer review", "todo"],
        ["Approved", "todo"]
      ],
      stock: 40,
      supply: [
        { label: "EDI 850 purchase order", tone: "idle", text: "Queued" },
        { label: "Supplier acknowledgment (855)", tone: "idle", text: "Pending" }
      ],
      extraTrace: [],
      approveLabel: "Approve and submit",
      canApprove: true
    },
    submitted: {
      header: { tone: "ok", text: "Approved and submitted" },
      stages: [
        { label: "1 · Clinical Sentinel", tone: "ok", text: "Dose adjustment approved" },
        { label: "2 · PA Resolver", tone: "ok", text: "Submitted" },
        { label: "3 · Supply Agent", tone: "info", text: "Order sent" }
      ],
      paSteps: [
        ["Gathering evidence", "done"],
        ["Package compiled", "done"],
        ["Approved to submit", "done"],
        ["Payer review", "current"],
        ["Approved", "todo"]
      ],
      stock: 40,
      supply: [
        { label: "EDI 850 purchase order", tone: "info", text: "Sent" },
        { label: "Supplier acknowledgment (855)", tone: "idle", text: "Pending" }
      ],
      extraTrace: [
        { who: "Clinician", action: "approved the adjusted dose" },
        { who: "PA Resolver", action: "submitted the FHIR package", detail: "Waiting on payer review" },
        { who: "Supply Agent", action: "sent the EDI 850 purchase order", detail: "Waiting on supplier acknowledgment" }
      ],
      approveLabel: "Submitted",
      canApprove: false
    }
  }
};
