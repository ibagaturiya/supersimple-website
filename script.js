document.addEventListener("DOMContentLoaded", function () {
  const grid = document.getElementById("projectGrid");
  const allProjects = Array.from(document.querySelectorAll(".project"));
  let projects = allProjects.slice();
  const toggle = document.getElementById("bubbleToggle");
  const filterBar = document.getElementById("filterBar");

  const isTouch = matchMedia("(pointer: coarse)").matches;

  if (!grid || !toggle) {
    console.error("Missing #projectGrid or #bubbleToggle in the HTML.");
    return;
  }

  // Keep toggle clickable above everything (mobile stacking contexts are weird)
  function ensureToggleOnTop() {
    const toggleWrap =
      document.querySelector(".center-toggle") ||
      toggle.closest(".center-toggle");
    if (!toggleWrap) return;
    toggleWrap.style.position = "fixed";
    toggleWrap.style.zIndex = "9999";
    toggleWrap.style.pointerEvents = "auto";
  }
  ensureToggleOnTop();
  window.addEventListener("resize", ensureToggleOnTop);

  // --- FILTER LOGIC ---
  function applyFilter(filter) {
    allProjects.forEach((el) => {
      const hashtags = (el.dataset.hashtags || "").toLowerCase();
      const shouldShow = !filter || hashtags.includes(filter);
      el.style.pointerEvents = shouldShow ? "" : "none";
      el.style.opacity = shouldShow ? "1" : "0.12";
      el.style.transition = "opacity 0.4s cubic-bezier(0.4,0,0.2,1)";
    });

    projects = allProjects;
    storeOriginalPositions();
    originalRects = projects.map((el) => el.getBoundingClientRect());
  }

  if (filterBar) {
    filterBar.addEventListener("click", function (e) {
      const btn = e.target.closest(".filter-btn");
      if (!btn) return;
      btn.classList.toggle("active");
      if (btn.classList.contains("active")) {
        applyFilter((btn.dataset.filter || "").toLowerCase());
      } else {
        applyFilter(null);
      }
    });
  }

  // --- BUBBLE PHYSICS LOGIC ---
  let originalRects = [];
  let engine = null,
    render = null,
    runner = null,
    bodies = [],
    mouseConstraint = null,
    walls = [];
  let scrollPosition = 0;
  let inBubbleMode = false;

  function lockBodyScroll() {
    scrollPosition =
      window.pageYOffset || document.documentElement.scrollTop || 0;
    document.body.style.overflow = "hidden";
    document.body.style.position = "fixed";
    document.body.style.top = `-${scrollPosition}px`;
    document.body.style.width = "100%";
  }

  function unlockBodyScroll() {
    document.body.style.overflow = "";
    document.body.style.position = "";
    document.body.style.top = "";
    document.body.style.width = "";
    window.scrollTo(0, scrollPosition);
  }

  function storeOriginalPositions() {
    if (!inBubbleMode) {
      projects = allProjects.filter((el) => el.style.display !== "none");
      originalRects = projects.map((el) => el.getBoundingClientRect());
    }
  }

  function handleOrientation(event) {
    if (!engine) return;
    // event.gamma / beta can be null on some devices
    const gx = typeof event.gamma === "number" ? event.gamma / 45 : 0;
    const gy = typeof event.beta === "number" ? event.beta / 45 : 0;
    engine.world.gravity.x = gx;
    engine.world.gravity.y = gy;
  }

  function handleMouseMove(event) {
    if (!engine) return;
    const x = (event.clientX / window.innerWidth - 0.5) * 2;
    const y = (event.clientY / window.innerHeight - 0.5) * 2;
    engine.world.gravity.x = x;
    engine.world.gravity.y = y;
  }

  // Throttle DOM writes to one per animation frame (huge for mobile)
  let rafPending = false;
  function syncDomFromBodies() {
    rafPending = false;
    bodies.forEach((body) => {
      const w = body.bounds.max.x - body.bounds.min.x;
      const h = body.bounds.max.y - body.bounds.min.y;

      // Use translate3d to reduce layout thrash vs left/top
      const x = body.position.x - w / 2;
      const y = body.position.y - h / 2;

      body.el.style.transform = `translate3d(${x}px, ${y}px, 0) rotate(${body.angle}rad)`;
    });
  }

  function startBubblePhysics() {
    inBubbleMode = true;
    ensureToggleOnTop();

    lockBodyScroll();

    grid.classList.add("bubble-mode");
    grid.style.position = "fixed";
    grid.style.left = "0";
    grid.style.top = "0";
    grid.style.width = "100vw";
    grid.style.height = "100vh";
    grid.style.zIndex = "100";

    engine = Matter.Engine.create();

    // Clean old canvas if any
    if (render && render.canvas && render.canvas.parentNode) {
      render.canvas.parentNode.removeChild(render.canvas);
    }

    render = Matter.Render.create({
      element: document.body,
      engine: engine,
      options: {
        width: window.innerWidth,
        height: window.innerHeight,
        wireframes: false,
        background: "transparent",
      },
    });

    const wallThickness = 100;
    const wallOptions = {
      isStatic: true,
      render: {
        fillStyle: "transparent",
        strokeStyle: "transparent",
        lineWidth: 0,
      },
    };

    walls = [
      Matter.Bodies.rectangle(
        window.innerWidth / 2,
        -wallThickness / 2,
        window.innerWidth,
        wallThickness,
        wallOptions,
      ),
      Matter.Bodies.rectangle(
        window.innerWidth / 2,
        window.innerHeight + wallThickness / 2,
        window.innerWidth,
        wallThickness,
        wallOptions,
      ),
      Matter.Bodies.rectangle(
        -wallThickness / 2,
        window.innerHeight / 2,
        wallThickness,
        window.innerHeight,
        wallOptions,
      ),
      Matter.Bodies.rectangle(
        window.innerWidth + wallThickness / 2,
        window.innerHeight / 2,
        wallThickness,
        window.innerHeight,
        wallOptions,
      ),
    ];

    Matter.World.add(engine.world, walls);

    bodies = projects.map((el, i) => {
      el.style.position = "absolute";
      el.style.transition = "none";
      el.style.zIndex = 10;

      const rect = originalRects[i];
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const w = rect.width;
      const h = rect.height;

      // Reset to transform-based positioning for bubble mode
      el.style.left = "0px";
      el.style.top = "0px";
      el.style.transform = `translate3d(${x - w / 2}px, ${y - h / 2}px, 0)`;

      const body = Matter.Bodies.rectangle(x, y, w, h, {
        restitution: 0.8,
        friction: 0.15,
        frictionAir: 0.02,
      });

      Matter.Body.setVelocity(body, { x: 0, y: 0 });
      Matter.Body.setAngularVelocity(body, 0);

      body.el = el;
      Matter.World.add(engine.world, body);
      return body;
    });

    // IMPORTANT: bind mouse/touch constraint to the canvas (best practice on mobile)
    mouseConstraint = Matter.MouseConstraint.create(engine, {
      element: render.canvas,
      constraint: { stiffness: 0.2, render: { visible: false } },
    });
    Matter.World.add(engine.world, mouseConstraint);

    Matter.Events.on(engine, "afterUpdate", () => {
      if (!rafPending) {
        rafPending = true;
        requestAnimationFrame(syncDomFromBodies);
      }
    });

    // Input: orientation for touch devices, mouse for desktop
    if (isTouch) {
      window.addEventListener("deviceorientation", handleOrientation);
    } else {
      window.addEventListener("mousemove", handleMouseMove);
    }

    Matter.Render.run(render);
    runner = Matter.Runner.create();
    Matter.Runner.run(runner, engine);

    // Kick bodies slightly
    setTimeout(() => {
      bodies.forEach((body) => {
        const angle = Math.random() * 2 * Math.PI;
        const force = 0.06 + Math.random() * 0.05; // slightly lower -> smoother on phones
        Matter.Body.applyForce(body, body.position, {
          x: Math.cos(angle) * force,
          y: Math.sin(angle) * force,
        });
        Matter.Body.setAngularVelocity(body, (Math.random() - 0.5) * 0.15);
      });
    }, 100);

    // DO NOT disable canvas pointer events on touch devices
    if (!isTouch && render.canvas) {
      setTimeout(() => {
        render.canvas.style.pointerEvents = "none";
      }, 200);
    }
  }

  function stopBubblePhysics() {
    inBubbleMode = false;
    ensureToggleOnTop(); // keep it clickable during teardown

    unlockBodyScroll();

    // Remove listeners
    window.removeEventListener("deviceorientation", handleOrientation);
    window.removeEventListener("mousemove", handleMouseMove);

    // Stop matter safely
    try {
      if (render) Matter.Render.stop(render);
      if (runner) Matter.Runner.stop(runner);
    } catch (e) {
      console.warn("Matter stop warning:", e);
    }

    // Remove canvas
    if (render && render.canvas && render.canvas.parentNode) {
      render.canvas.parentNode.removeChild(render.canvas);
    }

    // Clear engine refs
    try {
      if (engine && engine.events) engine.events = {};
    } catch (e) {}

    engine = null;
    render = null;
    runner = null;
    walls = [];
    bodies = [];
    mouseConstraint = null;

    // Restore project elements
    // If originalRects matches projects, animate back; otherwise reset
    if (projects.length === originalRects.length) {
      projects.forEach((el, i) => {
        el.style.transition = "transform 1s cubic-bezier(0.4,2,0.6,1)";
        const rect = originalRects[i];
        el.style.transform = `translate3d(${rect.left}px, ${rect.top}px, 0) rotate(0rad)`;
      });
    } else {
      projects.forEach((el) => {
        el.style.transition = "";
        el.style.transform = "";
      });
    }

    setTimeout(() => {
      projects.forEach((el) => {
        el.style.position = "";
        el.style.left = "";
        el.style.top = "";
        el.style.transition = "";
        el.style.zIndex = "";
        el.style.pointerEvents = "";
        el.style.transform = "";
      });

      grid.classList.remove("bubble-mode");
      grid.style.position = "";
      grid.style.left = "";
      grid.style.top = "";
      grid.style.width = "";
      grid.style.height = "";
      grid.style.zIndex = "";
      grid.style.pointerEvents = "";
    }, 1000);
  }

  window.addEventListener("resize", function () {
    if (!inBubbleMode) storeOriginalPositions();
  });
  window.addEventListener("load", storeOriginalPositions);

  toggle.addEventListener("change", function () {
    ensureToggleOnTop();

    if (toggle.checked) {
      document.body.classList.add("toggled");
      storeOriginalPositions();
      startBubblePhysics();
    } else {
      document.body.classList.remove("toggled");
      stopBubblePhysics();

      // If you *must* reload, keep it, but it’s usually not needed after proper cleanup.
      setTimeout(() => {
        location.reload();
      }, 1000);
    }
  });
});
