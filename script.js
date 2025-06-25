document.addEventListener("DOMContentLoaded", function () {
  const grid = document.getElementById("projectGrid");
  const allProjects = Array.from(document.querySelectorAll(".project"));
  let projects = allProjects.slice();
  const toggle = document.getElementById("bubbleToggle");
  const filterBar = document.getElementById("filterBar");
  let activeFilter = null;

  if (!grid || !toggle) {
    console.error("Missing #projectGrid or #bubbleToggle in the HTML.");
    return;
  }

  // --- FILTER LOGIC ---
  function applyFilter(filter) {
    // 1. Record the first (current) positions
    const firstRects = new Map();
    allProjects.forEach((el) => {
      firstRects.set(el, el.getBoundingClientRect());
    });

    // 2. Apply filter logic
    allProjects.forEach((el) => {
      const hashtags = (el.dataset.hashtags || "").toLowerCase();
      const shouldShow = !filter || hashtags.includes(filter);

      if (shouldShow) {
        // If hidden, show and animate in
        if (el.style.display === "none") {
          el.style.display = "";
          el.classList.add("appearing");
          // Force reflow to apply initial state
          void el.offsetWidth;
          el.classList.remove("vanish");
          // Animate to visible
          setTimeout(() => {
            el.classList.remove("appearing");
          }, 10); // Next tick
        } else {
          el.classList.remove("vanish");
          el.classList.remove("appearing");
        }
      } else {
        // Animate out
        el.classList.add("vanish");
        setTimeout(() => {
          el.style.display = "none";
          el.classList.remove("vanish");
        }, 400);
      }
    });

    // 3. Wait for the DOM to update, then animate grid relocation
    requestAnimationFrame(() => {
      allProjects.forEach((el) => {
        if (el.style.display === "none") return;
        const lastRect = el.getBoundingClientRect();
        const firstRect = firstRects.get(el);
        const dx = firstRect.left - lastRect.left;
        const dy = firstRect.top - lastRect.top;
        el.style.transition = "none";
        el.style.transform = `translate(${dx}px, ${dy}px)`;
        requestAnimationFrame(() => {
          el.style.transition = "transform 0.5s cubic-bezier(0.4,0,0.2,1)";
          el.style.transform = "";
        });
      });
    });

    projects = allProjects.filter((el) => el.style.display !== "none");
    storeOriginalPositions();
    originalRects = projects.map((el) => el.getBoundingClientRect());
  }

  if (filterBar) {
    filterBar.addEventListener("click", function (e) {
      const btn = e.target.closest(".filter-btn");
      if (!btn) return;

      if (btn.classList.contains("active")) {
        btn.classList.remove("active");
        activeFilter = null;
        document
          .querySelectorAll(".filter-group")
          .forEach((g) => g.classList.remove("open"));
        applyFilter(null);
      } else {
        document
          .querySelectorAll(".filter-btn")
          .forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        activeFilter = btn.dataset.filter.toLowerCase();
        document
          .querySelectorAll(".filter-group")
          .forEach((g) => g.classList.remove("open"));
        applyFilter(activeFilter);
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
    lockBodyScroll();

    grid.classList.add("bubble-mode");
    grid.style.position = "fixed";
    grid.style.left = "0";
    grid.style.top = "0";
    grid.style.width = "100vw";
    grid.style.height = "100vh";
    grid.style.zIndex = "100";

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
        wallOptions
      ),
      Matter.Bodies.rectangle(
        window.innerWidth / 2,
        window.innerHeight + wallThickness / 2,
        window.innerWidth,
        wallThickness,
        wallOptions
      ),
      Matter.Bodies.rectangle(
        -wallThickness / 2,
        window.innerHeight / 2,
        wallThickness,
        window.innerHeight,
        wallOptions
      ),
      Matter.Bodies.rectangle(
        window.innerWidth + wallThickness / 2,
        window.innerHeight / 2,
        wallThickness,
        window.innerHeight,
        wallOptions
      ),
    ];
    Matter.World.add(engine.world, walls);

    bodies = projects.map((el, i) => {
      el.style.position = "absolute";
      el.style.transition = "none";
      el.style.zIndex = 10;

      // Use stored originalRects instead of getBoundingClientRect()
      const rect = originalRects[i];
      // These are already relative to the viewport
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const w = rect.width;
      const h = rect.height;

      el.style.left = x - w / 2 + "px";
      el.style.top = y - h / 2 + "px";

      const body = Matter.Bodies.rectangle(x, y, w, h, {
        restitution: 0.8,
        friction: 0.01,
        frictionAir: 0.00002,
      });
      Matter.Body.setVelocity(body, { x: 0, y: 0 });
      Matter.Body.setAngularVelocity(body, 0);

      body.el = el;
      Matter.World.add(engine.world, body);
      return body;
    });

    mouseConstraint = Matter.MouseConstraint.create(engine, {
      element: document.body,
      constraint: { stiffness: 0.2, render: { visible: false } },
    });
    Matter.World.add(engine.world, mouseConstraint);

    // --- ROTATION LOGIC ---
    Matter.Events.on(engine, "afterUpdate", () => {
      bodies.forEach((body) => {
        const w = body.bounds.max.x - body.bounds.min.x;
        const h = body.bounds.max.y - body.bounds.min.y;
        body.el.style.left = body.position.x - w / 2 + "px";
        body.el.style.top = body.position.y - h / 2 + "px";
        body.el.style.transform = `rotate(${body.angle}rad)`;
      });
    });

    window.addEventListener("deviceorientation", handleOrientation);
    window.addEventListener("mousemove", handleMouseMove);

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
        // Give initial random angular velocity for visible rotation
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
    document.querySelector(".center-toggle").style.pointerEvents = "auto";
    unlockBodyScroll();
    disableTouchLock();

    window.removeEventListener("deviceorientation", handleOrientation);
    window.removeEventListener("mousemove", handleMouseMove);

    Matter.Render.stop(render);
    Matter.Runner.stop(runner);
    if (render && render.canvas && render.canvas.parentNode) {
      render.canvas.parentNode.removeChild(render.canvas);
    }
    engine.events = {};

    // Animate back to grid
    if (projects.length === originalRects.length) {
      projects.forEach((el, i) => {
        el.style.transition = "all 1s cubic-bezier(0.4,2,0.6,1)";
        const rect = originalRects[i];
        el.style.left = rect.left + "px";
        el.style.top = rect.top + "px";
        el.style.transform = ""; // Reset rotation
      });
    } else {
      projects.forEach((el) => {
        el.style.transition = "";
        el.style.left = "";
        el.style.top = "";
        el.style.transform = ""; // Reset rotation
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
        el.style.transform = ""; // Reset rotation
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

  // Only store positions when not in bubble mode
  window.addEventListener("resize", function () {
    if (!inBubbleMode) storeOriginalPositions();
  });

  // Only store positions after everything is loaded
  window.addEventListener("load", storeOriginalPositions);

  toggle.addEventListener("change", function () {
    if (toggle.checked) {
      document.body.classList.add("toggled");
      storeOriginalPositions();
      startBubblePhysics();
    } else {
      document.body.classList.remove("toggled");
      stopBubblePhysics();
      setTimeout(() => {
        location.reload();
      }, 1000); // Match the timeout in stopBubblePhysics
    }
  });
});
