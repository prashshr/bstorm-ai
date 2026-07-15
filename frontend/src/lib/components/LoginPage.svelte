<script lang="ts">
  import AuthCard from "./AuthCard.svelte";
</script>

<main class="login-page">
  <AuthCard />
  <footer class="login-footer">
    AI-Ensemble · production multi-provider AI discussions
  </footer>
</main>

<style>
  .login-page {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .login-footer {
    text-align: center;
    padding: 16px;
    color: var(--text-tertiary);
    font-size: 12px;
  }
</style>
