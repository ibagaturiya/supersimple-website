(() => {
  const gallery = document.getElementById("drone-gallery");
  const sortButton = document.getElementById("gallery-sort");
  const viewer = document.getElementById("gallery-viewer");
  const viewerImage = document.getElementById("viewer-image");
  const viewerDate = document.getElementById("viewer-date");
  const viewerCounter = document.getElementById("viewer-counter");
  const closeButton = document.getElementById("viewer-close");
  const previousButton = document.getElementById("viewer-prev");
  const nextButton = document.getElementById("viewer-next");

  if (!gallery || !viewer) return;

  let cards = Array.from(gallery.querySelectorAll(".drone-card"));
  let newestFirst = true;
  let currentIndex = 0;
  let previousFocus = null;
  let touchStartX = 0;
  let touchStartY = 0;

  const refreshCards = () => {
    cards = Array.from(gallery.querySelectorAll(".drone-card"));
    cards.forEach((card, index) => { card.dataset.index = index; });
  };

  const showImage = (index) => {
    currentIndex = (index + cards.length) % cards.length;
    const card = cards[currentIndex];
    const image = card.querySelector("img");
    const time = card.querySelector("time");
    viewerImage.src = image.currentSrc || image.src;
    viewerImage.alt = image.alt;
    viewerDate.dateTime = time.dateTime;
    viewerDate.textContent = time.textContent;
    viewerCounter.textContent = `${currentIndex + 1} / ${cards.length}`;

    [cards[currentIndex - 1], cards[currentIndex + 1]].forEach((nearbyCard) => {
      if (!nearbyCard) return;
      const preload = new Image();
      preload.src = nearbyCard.querySelector("img").src;
    });
  };

  const openViewer = (card) => {
    previousFocus = card;
    showImage(Number(card.dataset.index));
    viewer.classList.add("is-open");
    viewer.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    closeButton.focus({ preventScroll: true });
  };

  const closeViewer = () => {
    viewer.classList.remove("is-open");
    viewer.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    viewerImage.src = "";
    previousFocus?.focus({ preventScroll: true });
  };

  gallery.addEventListener("click", (event) => {
    const card = event.target.closest(".drone-card");
    if (card) openViewer(card);
  });

  sortButton?.addEventListener("click", () => {
    newestFirst = !newestFirst;
    const direction = newestFirst ? -1 : 1;
    cards
      .sort((a, b) => direction * a.dataset.created.localeCompare(b.dataset.created))
      .forEach((card) => gallery.appendChild(card));
    refreshCards();
    sortButton.innerHTML = newestFirst
      ? 'newest first <span aria-hidden="true">↓</span>'
      : 'oldest first <span aria-hidden="true">↑</span>';
  });

  closeButton.addEventListener("click", closeViewer);
  previousButton.addEventListener("click", () => showImage(currentIndex - 1));
  nextButton.addEventListener("click", () => showImage(currentIndex + 1));
  viewer.addEventListener("click", (event) => {
    if (event.target === viewer) closeViewer();
  });

  document.addEventListener("keydown", (event) => {
    if (!viewer.classList.contains("is-open")) return;
    if (event.key === "Escape") closeViewer();
    else if (event.key === "ArrowLeft") showImage(currentIndex - 1);
    else if (event.key === "ArrowRight") showImage(currentIndex + 1);
  });

  viewer.addEventListener("touchstart", (event) => {
    touchStartX = event.changedTouches[0].clientX;
    touchStartY = event.changedTouches[0].clientY;
  }, { passive: true });

  viewer.addEventListener("touchend", (event) => {
    const deltaX = event.changedTouches[0].clientX - touchStartX;
    const deltaY = event.changedTouches[0].clientY - touchStartY;
    if (Math.abs(deltaX) > 48 && Math.abs(deltaX) > Math.abs(deltaY)) {
      showImage(currentIndex + (deltaX < 0 ? 1 : -1));
    }
  }, { passive: true });

  refreshCards();
})();
