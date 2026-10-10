//! Reads a Google sign-in token on stdin and prints the Android Auto download link.
//! No account, APK, URL cache or credentials are bundled.
use gpapi::Gpapi;
use serde::Deserialize;
use serde_json::json;
use std::io::{self, IsTerminal, Read, Write};
use std::time::Duration;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    email: String,
    token: String,
    remember: bool,
}

async fn resolve(request: Request) -> Result<serde_json::Value, ()> {
    let mut api = Gpapi::new("px_9a", &request.email);
    if request.token.starts_with("oauth2_4/") {
        api.request_aas_token(request.token).await.map_err(|_| ())?;
    } else if request.token.starts_with("aas_et/") {
        api.set_aas_token(request.token);
    } else {
        return Err(());
    }
    // Deliberately no ToS acceptance: the user accepts Play terms on their own account.
    api.login().await.map_err(|_| ())?;
    writeln!(io::stdout(), "{{\"stage\":\"resolving\"}}").map_err(|_| ())?;
    io::stdout().flush().map_err(|_| ())?;
    let (url, _, _, _) = api
        .get_download_info("com.google.android.projection.gearhead", None)
        .await
        .map_err(|_| ())?;
    let mut result = json!({"status": "ok", "url": url.ok_or(())?});
    if request.remember {
        result["aas_token"] = json!(api.get_aas_token().ok_or(())?);
    }
    Ok(result)
}

#[tokio::main]
async fn main() {
    // Silence panics so errors never disclose responses, cookies or credentials.
    std::panic::set_hook(Box::new(|_| {}));
    if io::stdin().is_terminal() || io::stdout().is_terminal() {
        std::process::exit(2);
    }
    let mut input = String::new();
    if io::stdin().take(4097).read_to_string(&mut input).is_err() || input.len() > 4096 {
        std::process::exit(2);
    }
    let request = match serde_json::from_str::<Request>(&input) {
        Ok(request) => request,
        Err(_) => std::process::exit(2),
    };
    drop(input);
    match tokio::time::timeout(Duration::from_secs(110), resolve(request)).await {
        Ok(Ok(result)) => {
            if writeln!(io::stdout(), "{result}").is_err() {
                std::process::exit(1);
            }
        }
        _ => std::process::exit(1),
    }
}
