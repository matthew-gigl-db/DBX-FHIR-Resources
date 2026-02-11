from shiny import App, ui, render, Inputs, Outputs, Session
from shiny import reactive
from jwcrypto import jwk
import json

# Path to your PEM public key (matching your private key)
PUBLIC_KEY_PATH = "public_key.pem"
KID = "epic-key-1"   # must match JWT header "kid"
ALG = "RS384"        # or RS256 if that’s what you registered

def load_jwks():
    with open(PUBLIC_KEY_PATH, "rb") as f:
        pub_pem = f.read()

    key = jwk.JWK.from_pem(pub_pem)
    key.use = "sig"
    key.alg = ALG
    key.kid = KID

    return {"keys": [json.loads(key.export_public())]}

JWKS = load_jwks()

# Minimal UI just to show the JWKS; Epic will call the JSON endpoint
app_ui = ui.page_fluid(
    ui.h2("Epic JWKS endpoint"),
    ui.p("This app serves JWKS for Epic backend services."),
    ui.output_text_verbatim("jwks_preview")
)

def server(input: Inputs, output: Outputs, session: Session):

    @output
    @render.text
    def jwks_preview():
        return json.dumps(JWKS, indent=2)

    # Expose a raw JWKS endpoint for Epic (Starlette route)
    @session.app.router.get("/.well-known/jwks.json")
    async def jwks_route(request):
        from starlette.responses import JSONResponse
        return JSONResponse(JWKS)