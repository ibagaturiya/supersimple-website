document.addEventListener("DOMContentLoaded", function () {
  const grid = document.getElementById("projectGrid");
  const allProjects = Array.from(document.querySelectorAll(".project"));
  let projects = allProjects.slice();
  const filterBar = document.getElementById("filterBar");
  const toggleButton = document.querySelector(
    '.filter-btn[data-action="toggle"]',
  );
  let activeFilter = null;
  let bubbleModeActive = false;

  if (!grid) {
    console.error("Missing #projectGrid in the HTML.");
    return;
  }

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

      if (btn.dataset.action === "toggle") {
        const shouldActivate = !btn.classList.contains("active");
        filterBar.querySelectorAll(".filter-btn").forEach((filterBtn) => {
          if (filterBtn !== btn) filterBtn.classList.remove("active");
        });

        if (shouldActivate) {
          btn.classList.add("active");
          applyFilter(null);
          setBubbleMode(true);
        } else {
          btn.classList.remove("active");
          setBubbleMode(false);
        }
        return;
      }

      const isActive = btn.classList.contains("active");
      filterBar.querySelectorAll(".filter-btn").forEach((filterBtn) => {
        if (filterBtn !== btn) filterBtn.classList.remove("active");
      });

      if (!isActive) {
        btn.classList.add("active");
        applyFilter(btn.dataset.filter.toLowerCase());
      } else {
        applyFilter(null);
      }
    });
  }

  // --- BUBBLE PHYSICS LOGIC ---
  let originalRects = [];
  let engine,
    render,
    runner,
    bodies = [],
    mouseConstraint,
    walls = [];
  let scrollPosition = 0;
  let inBubbleMode = false;

  function lockBodyScroll() {
    scrollPosition = window.pageYOffset;
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

  function preventTouchMove(e) {
    if (!e.target.closest(".center-toggle")) {
      e.preventDefault();
    }
  }

  function enableTouchLock() {
    document.body.addEventListener("touchmove", preventTouchMove, {
      passive: false,
    });
  }
  function disableTouchLock() {
    document.body.removeEventListener("touchmove", preventTouchMove, {
      passive: false,
    });
  }

  function storeOriginalPositions() {
    if (!inBubbleMode) {
      projects = allProjects.filter((el) => el.style.display !== "none");
      originalRects = projects.map((el) => el.getBoundingClientRect());
    }
  }

  function startBubblePhysics() {
    inBubbleMode = true;
    if (window.innerWidth > 768) {
      lockBodyScroll();
      grid.style.position = "fixed";
      grid.style.left = "0";
      grid.style.top = "0";
      grid.style.width = "100vw";
      grid.style.height = "100vh";
      grid.style.zIndex = "100";
    }
    grid.classList.add("bubble-mode");
    engine = Matter.Engine.create();
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
    if (render.canvas) {
      render.canvas.style.pointerEvents = "none";
      render.canvas.style.zIndex = "-1";
      render.canvas.style.position = "fixed";
    }
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
        -wallThickness / 30,
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
      el.style.pointerEvents = "auto";
      el.querySelectorAll("*").forEach((child) => {
        child.style.pointerEvents = "none";
      });
      const rect = originalRects[i];
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const w = rect.width;
      const h = rect.height;
      el.style.left = x - w / 2 + "px";
      el.style.top = y - h / 2 + "px";
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
    if (window.innerWidth > 768) {
      mouseConstraint = Matter.MouseConstraint.create(engine, {
        element: document.body,
        constraint: { stiffness: 0.2, render: { visible: false } },
      });
      Matter.World.add(engine.world, mouseConstraint);
    }
    Matter.Events.on(engine, "afterUpdate", () => {
      bodies.forEach((body) => {
        const w = body.bounds.max.x - body.bounds.min.x;
        const h = body.bounds.max.y - body.bounds.min.y;
        body.el.style.left = body.position.x - w / 2 + "px";
        body.el.style.top = body.position.y - h / 2 + "px";
        body.el.style.transform = `rotate(${body.angle}rad)`;
      });
    });
    console.log("Bubble mode started", {
      width: window.innerWidth,
      height: window.innerHeight,
    });
    window.addEventListener("deviceorientation", handleOrientation);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("touchmove", (e) => {
      if (!engine) return;
      const t = e.touches && e.touches[0];
      if (!t) return;

      const x = (t.clientX / window.innerWidth - 0.5) * 2;
      const y = (t.clientY / window.innerHeight - 0.5) * 2;

      engine.world.gravity.x = x;
      engine.world.gravity.y = y;
    });
    Matter.Render.run(render);
    runner = Matter.Runner.create();
    Matter.Runner.run(runner, engine);
    setTimeout(() => {
      bodies.forEach((body) => {
        const angle = Math.random() * 2 * Math.PI;
        const force = 0.08 + Math.random() * 0.07;
        Matter.Body.applyForce(body, body.position, {
          x: Math.cos(angle) * force,
          y: Math.sin(angle) * force,
        });
        Matter.Body.setAngularVelocity(body, (Math.random() - 0.5) * 0.2);
      });
    }, 100);
    setTimeout(() => {
      if (render.canvas) {
        render.canvas.style.pointerEvents = "none";
      }
    }, 200);
  }

  function stopBubblePhysics() {
    inBubbleMode = false;
    if (window.innerWidth > 768) {
      unlockBodyScroll();
    }
    disableTouchLock();
    window.removeEventListener("deviceorientation", handleOrientation);
    window.removeEventListener("mousemove", handleMouseMove);
    Matter.Render.stop(render);
    Matter.Runner.stop(runner);
    if (render && render.canvas && render.canvas.parentNode) {
      render.canvas.parentNode.removeChild(render.canvas);
    }
    engine.events = {};
    if (projects.length === originalRects.length) {
      projects.forEach((el, i) => {
        el.style.transition = "all 1s cubic-bezier(0.4,2,0.6,1)";
        const rect = originalRects[i];
        el.style.left = rect.left + "px";
        el.style.top = rect.top + "px";
        el.style.transform = "";
      });
    } else {
      projects.forEach((el) => {
        el.style.transition = "";
        el.style.left = "";
        el.style.top = "";
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
        el.querySelectorAll("*").forEach((child) => {
          child.style.pointerEvents = "";
        });
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

  function handleOrientation(event) {
    if (!engine) return;
    engine.world.gravity.x = event.gamma / 45;
    engine.world.gravity.y = event.beta / 45;
  }

  function handleMouseMove(event) {
    if (!engine) return;
    const x = (event.clientX / window.innerWidth - 0.5) * 2;
    const y = (event.clientY / window.innerHeight - 0.5) * 2;
    engine.world.gravity.x = x;
    engine.world.gravity.y = y;
  }

  window.addEventListener("resize", function () {
    if (!inBubbleMode) storeOriginalPositions();
  });
  window.addEventListener("load", storeOriginalPositions);

  function setBubbleMode(active) {
    if (bubbleModeActive === active) return;
    bubbleModeActive = active;

    if (active) {
      document.body.classList.add("toggled");
      storeOriginalPositions();
      startBubblePhysics();
    } else {
      document.body.classList.remove("toggled");
      stopBubblePhysics();
      setTimeout(() => {
        location.reload();
      }, 1000);
    }
  }

  if (toggleButton) {
    toggleButton.addEventListener("click", function () {
      const shouldActivate = !toggleButton.classList.contains("active");
      if (shouldActivate) {
        setBubbleMode(true);
      } else {
        setBubbleMode(false);
      }
    });
  }
});
