(() => {
    const account = document.querySelector("[data-aa-account]");
    if (!account) return;
    const summary = account.querySelector("summary");

    document.addEventListener("click", (event) => {
        if (account.open && !account.contains(event.target) && !document.querySelector("dialog[open]")) {
            account.open = false;
        }
    });

    account.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && account.open) {
            event.preventDefault();
            account.open = false;
            summary.focus();
        }
    });
})();
