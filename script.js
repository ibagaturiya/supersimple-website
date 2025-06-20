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
    allProjects.forEach((el) => {
      const hashtags = (el.dataset.hashtags || "").toLowerCase();
      if (!filter || hashtags.includes(filter)) {
        el.style.display = "";
      } else {
        el.style.display = "none";
      }
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
    enableTouchLock();

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

      const rect = el.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const r = rect.width / 2;

      el.style.left = x - r + "px";
      el.style.top = y - r + "px";

      const body = Matter.Bodies.circle(x, y, r, {
        restitution: 0.8,
        friction: 0.01,
        frictionAir: 0.01,
      });
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
        const r = body.circleRadius;
        body.el.style.left = body.position.x - r + "px";
        body.el.style.top = body.position.y - r + "px";
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
      storeOriginalPositions();
      startBubblePhysics();
    } else {
      stopBubblePhysics();
      setTimeout(() => {
        location.reload();
      }, 1000); // Match the timeout in stopBubblePhysics
    }
  });
});
