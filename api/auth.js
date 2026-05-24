// api/auth.js — Vercel serverless function for Decap CMS OAuth
// Handles GitHub OAuth flow so Decap CMS can authenticate

export default async function handler(req, res) {
  const { code, provider } = req.query;

  if (!code) {
    // Step 1: redirect to GitHub OAuth
    const params = new URLSearchParams({
      client_id: process.env.GITHUB_CLIENT_ID,
      scope: 'repo,user',
      redirect_uri: `${process.env.SITE_URL}/api/auth`,
    });
    return res.redirect(`https://github.com/login/oauth/authorize?${params}`);
  }

  // Step 2: exchange code for token
  try {
    const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        client_id:     process.env.GITHUB_CLIENT_ID,
        client_secret: process.env.GITHUB_CLIENT_SECRET,
        code,
      }),
    });

    const data = await tokenRes.json();

    if (data.error) {
      return res.status(400).send(`OAuth error: ${data.error_description}`);
    }

    // Step 3: send token back to Decap CMS via postMessage
    const token = data.access_token;
    const script = `
      <script>
        (function() {
          function receiveMessage(e) {
            console.log("receiveMessage %o", e);
            window.opener.postMessage(
              'authorization:github:success:${JSON.stringify({ token, provider: "github" })}',
              e.origin
            );
          }
          window.addEventListener("message", receiveMessage, false);
          window.opener.postMessage("authorizing:github", "*");
        })()
      </script>`;
    return res.send(script);
  } catch (err) {
    return res.status(500).send(`Server error: ${err.message}`);
  }
}