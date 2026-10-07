# Local and optional integrations

## Python service first

Run `python app.py train`, then `python app.py serve`. Health: `http://127.0.0.1:8105/health`.

## Optional local LLM (automation projects only)

The default examples do not need a key or internet. Model projects 01/02 do not use an LLM.

For projects 03/04/05, start an OpenAI-compatible server such as LM Studio, load an instruction model that your machine can run, and enable its local server. In PowerShell, in the same terminal where you will start the Python service:

```powershell
$env:ENABLE_LLM="1"
$env:LLM_BASE_URL="http://127.0.0.1:1234/v1"
$env:LLM_MODEL="exact-model-id-from-your-server"
# Only if your endpoint requires authentication:
# $env:LLM_API_KEY="your-key"
.\.venv\Scripts\python.exe app.py serve
```

The endpoint must implement POST `/chat/completions` and return `choices[0].message.content` containing a JSON object. No SDK, provider membership or commercial model is required. Response format support varies; this implementation validates JSON itself and reports invalid responses. Connection timeout: 45 seconds. Adapter tests mock the transport; no actual LLM model was tested here.

`ENABLE_LLM=0` restores the fully local mode. Never commit a real key or a customer prompt. If using a hosted endpoint, confirm where customer data is sent.

## n8n bridge (projects 03/04/05)

1. Import `workflows/n8n_webhook.json` via n8n's workflow import action. Import UI names may vary by release.
2. In the **Local Python Service** HTTP node, set the service URL.
   - n8n via Node.js on the same Windows host: `http://127.0.0.1:8105` plus the supplied route.
   - n8n in Docker Desktop on Windows: `http://host.docker.internal:8105` plus the route. The service may need `APP_HOST=0.0.0.0` to accept container traffic; keep firewall access limited to your local environment. Default remains loopback.
   - Both apps in containers: use the Python container's service name and port on their private Docker network.
3. Start the Python service. Choose **Listen for test event** on the webhook. Copy the exact test URL displayed by your n8n instance.
4. Send the JSON in `workflows/sample_request.json` using an HTTP client or PowerShell:

```powershell
$body = Get-Content .\workflows\sample_request.json -Raw
Invoke-RestMethod -Method Post -Uri "PASTE_YOUR_N8N_TEST_WEBHOOK_URL" -ContentType "application/json" -Body $body
```

5. Inspect all three node outputs. Validation failures deliberately stop the normal HTTP path; add an error workflow/dead-letter queue before live use.
6. Publish/activate only after testing and adding webhook authentication in n8n. No real account or credential is configured in the JSON.

IDs must stay the same for retries of one event. Use a new ID for a new event; changing a payload while keeping its ID is rejected. Sample IDs are fixed and intentionally repeat-safe.

The bridge does **not** connect Telegram, Gmail, Supabase, Google Sheets or WhatsApp. Add those nodes yourself after local validation. Lead workflow responds with `client_reply` only. Do not send `internal` to clients. Ticket and invoice workflow responses are intended for an operator, not a public customer.

Workflow JSON structure was checked locally. Execution/import in an n8n instance, external credentials and real LLM generation remain untested.
