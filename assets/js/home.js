const welcomeBox = document.getElementById("welcome-text");
const hoverArea = document.querySelector("#welcome-hover-area");

let isLockedPaused = false;
let animation = null;

async function loadFlowText(filePath) {
  const response = await fetch(filePath);
  const text = await response.text();

  const visibleText = text
    .split("\n")
    .filter(line => !line.trim().startsWith("@"))
    .join("\n");

  welcomeBox.textContent = visibleText;

  animation = welcomeBox.animate(
    [
      { transform: "translateY(100%)" },
      { transform: "translateY(-100%)" }
    ],
    {
      duration: 150000,
      easing: "linear",
      fill: "forwards"
    }
  );
}

hoverArea.addEventListener("mouseenter", () => {
    if (animation) {
        animation.pause();
    }
});

hoverArea.addEventListener("mouseleave", () => {
    if (animation && !isLockedPaused) {
        animation.play();
    }
});

hoverArea.addEventListener("click", () => {
    if (!animation) return;

    isLockedPaused = !isLockedPaused;

    if (isLockedPaused) {
        animation.pause();
    } else {
        animation.play();
    }
});

loadFlowText("contents/home/welcome.txt");