<script lang="ts">
  import AuthCard from "./AuthCard.svelte";
  import Icon from "./Icon.svelte";

  const features = [
    {
      icon: "bot",
      title: "Every model, one prompt",
      body: "Run the same question across GPT, Claude, Gemini, Llama and 370+ models in parallel — not one vendor's opinion.",
    },
    {
      icon: "star",
      title: "Consensus synthesis",
      body: "A final synthesis pass weighs every answer and hands you one agreed, cited conclusion instead of a wall of tabs.",
    },
    {
      icon: "search",
      title: "Live web context",
      body: "Optional retrieval grounds the discussion in current sources, so answers reflect what is true today.",
    },
    {
      icon: "key",
      title: "Your keys, your data",
      body: "Provider credentials are encrypted per user. Self-hosted, no middleman, no training on your conversations.",
    },
  ];
</script>

<main class="login-page">
  <div class="landing">
    <section class="pitch">
      <div class="brand">
        <span class="brand-mark">⬡</span> AI-Ensemble
      </div>
      <h1 class="headline">
        One question.<br />
        Every model.<br />
        <em>One answer.</em>
      </h1>
      <p class="lede">
        Stop comparing chatbots in ten tabs. AI-Ensemble puts the whole
        council in one room, lets them argue, and returns a single synthesis
        you can trust.
      </p>
      <ul class="features">
        {#each features as f (f.title)}
          <li class="feature">
            <span class="feature-icon"><Icon name={f.icon} size="md" /></span>
            <div>
              <div class="feature-title">{f.title}</div>
              <div class="feature-body">{f.body}</div>
            </div>
          </li>
        {/each}
      </ul>
      <div class="social">
        <span class="stat"><strong>370+</strong> models</span>
        <span class="stat"><strong>7</strong> providers</span>
        <span class="stat"><strong>1</strong> consensus</span>
      </div>
    </section>

    <section class="auth-side">
      <div class="auth-intro">
        <h2>Sign in to start</h2>
        <p>Bring your own provider keys — or use the shared credits.</p>
      </div>
      <AuthCard />
    </section>
  </div>
  <footer class="login-footer">
    AI-Ensemble · production multi-provider AI discussions
  </footer>
</main>

<style>
  .login-page {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow-y: auto;
    background:
      radial-gradient(1200px 600px at 15% -10%, rgba(179, 93, 37, 0.14), transparent 60%),
      radial-gradient(900px 500px at 110% 110%, rgba(179, 93, 37, 0.08), transparent 55%),
      var(--bg-primary);
  }
  .landing {
    flex: 1;
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
    gap: 48px;
    align-items: center;
    width: min(1180px, 100%);
    margin: 0 auto;
    padding: 48px 32px 24px;
  }
  .pitch {
    display: flex;
    flex-direction: column;
    gap: 20px;
    min-width: 0;
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
  }
  .brand-mark {
    font-size: 18px;
  }
  .headline {
    margin: 0;
    font-size: clamp(34px, 4.6vw, 56px);
    line-height: 1.08;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .headline em {
    font-style: normal;
    color: var(--accent);
  }
  .lede {
    margin: 0;
    max-width: 52ch;
    color: var(--text-secondary);
    font-size: 16px;
    line-height: 1.6;
  }
  .features {
    list-style: none;
    margin: 8px 0 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
  }
  .feature {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: color-mix(in srgb, var(--bg-secondary) 75%, transparent);
  }
  .feature-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    flex: none;
    border-radius: 9px;
    background: color-mix(in srgb, var(--accent) 16%, transparent);
    color: var(--accent);
  }
  .feature-title {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 3px;
  }
  .feature-body {
    font-size: 12.5px;
    line-height: 1.5;
    color: var(--text-secondary);
  }
  .social {
    display: flex;
    gap: 22px;
    margin-top: 4px;
  }
  .stat {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    font-size: 12px;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .stat strong {
    font-size: 20px;
    color: var(--text-primary);
    letter-spacing: 0;
  }
  .auth-side {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    min-width: 0;
  }
  .auth-intro {
    text-align: center;
  }
  .auth-intro h2 {
    margin: 0 0 4px;
    font-size: 20px;
  }
  .auth-intro p {
    margin: 0;
    font-size: 13px;
    color: var(--text-secondary);
  }
  .login-footer {
    text-align: center;
    padding: 16px;
    color: var(--text-tertiary);
    font-size: 12px;
  }

  @media (max-width: 920px) {
    .landing {
      grid-template-columns: 1fr;
      gap: 28px;
      padding: 32px 20px 16px;
    }
    .features {
      grid-template-columns: 1fr;
    }
    .social {
      justify-content: center;
    }
    .headline {
      text-align: center;
    }
    .lede {
      margin-inline: auto;
      text-align: center;
    }
    .brand {
      justify-content: center;
      width: 100%;
    }
  }
</style>
