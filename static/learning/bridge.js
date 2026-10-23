(() => {
  const form = document.querySelector(".quest-form");
  if (!form) return;

  const prompt = form.querySelector("#prompt");
  const chips = [...form.querySelectorAll("[data-prompt-chip]")];
  const meter = form.querySelector("[data-signal-meter]");
  const dot = form.querySelector("[data-signal-dot]");
  const label = form.querySelector("[data-signal-label]");
  const count = form.querySelector("[data-prompt-count]");
  const submit = form.querySelector("[data-route-submit]");
  const submitLabel = form.querySelector("[data-submit-label]");
  const spinner = form.querySelector("[data-submit-spinner]");
  const arrow = form.querySelector("[data-submit-arrow]");

  const setChipState = (selectedChip = null) => {
    chips.forEach((chip) => chip.setAttribute("aria-pressed", String(chip === selectedChip)));
  };

  const updateSignal = () => {
    const value = prompt.value.trim();
    const characters = prompt.value.length;
    count.textContent = `${characters.toLocaleString()} / 2000`;

    let message = "AWAITING TRANSMISSION";
    let color = "bg-slate-500";
    if (value.length > 0 && value.length < 8) {
      message = "SIGNAL TOO SHORT · ADD A GOAL";
      color = "bg-orange-400";
    } else if (value.length >= 8 && value.length < 45) {
      message = "SIGNAL ACQUIRED · ADD DETAILS";
      color = "bg-amber-300";
    } else if (value.length >= 45) {
      message = "CLEAR SIGNAL · READY TO PLOT";
      color = "bg-teal-300";
    }

    label.textContent = message;
    dot.className = `h-1.5 w-1.5 flex-none rounded-full transition-colors ${color}`;
    meter.style.width = `${value.length ? Math.max(6, Math.min(100, (value.length / 180) * 100)) : 0}%`;
  };

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      prompt.value = chip.dataset.prompt || "";
      setChipState(chip);
      updateSignal();
      prompt.focus();
    });
  });

  prompt.addEventListener("input", () => {
    setChipState();
    updateSignal();
  });

  form.addEventListener("submit", (event) => {
    if (prompt.value.trim().length < 8) {
      event.preventDefault();
      label.textContent = "ADD AT LEAST 8 CHARACTERS";
      dot.className = "h-1.5 w-1.5 flex-none rounded-full bg-orange-400";
      prompt.focus();
      return;
    }
    submit.disabled = true;
    submitLabel.textContent = "Transmitting flight plan…";
    spinner.classList.remove("hidden");
    arrow.classList.add("hidden");
  });

  updateSignal();
})();
