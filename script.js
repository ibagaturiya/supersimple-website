document.addEventListener("DOMContentLoaded", function () {
  console.log("External script loaded");

  const grid = document.getElementById("projectGrid");
  const projects = Array.from(document.querySelectorAll(".project"));
  const toggle = document.getElementById("bubbleToggle");

  if (!grid || !toggle) {
    console.error("Missing #projectGrid or #bubbleToggle in the HTML.");
    return;
  }

  let originalRects = [];
  let engine,
    render,
    runner,
    bodies = [],
    mouseConstraint,
    walls = [];
  let scrollPosition = 0;

  // --- SCROLL LOCK FUNCTIONS ---
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
    e.preventDefault();
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

  // --- BUBBLE PHYSICS FUNCTIONS ---
  function storeOriginalPositions() {
    originalRects = projects.map((el) => el.getBoundingClientRect());
  }

  function startBubblePhysics() {
    document.querySelector(".center-toggle").style.pointerEvents = "auto";

    lockBodyScroll();
    enableTouchLock();

    grid.classList.add("bubble-mode");
    grid.style.position = "fixed";
    grid.style.left = "0";
    grid.style.top = "0";
    grid.style.width = "100vw";
    grid.style.height = "100vh";
    grid.style.zIndex = "100";
    grid.style.pointerEvents = "none";

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

    // Create boundaries (walls) at viewport edges
    const wallThickness = 100;
    walls = [
      Matter.Bodies.rectangle(
        window.innerWidth / 2,
        -wallThickness / 2,
        window.innerWidth,
        wallThickness,
        { isStatic: true }
      ),
      Matter.Bodies.rectangle(
        window.innerWidth / 2,
        window.innerHeight + wallThickness / 2,
        window.innerWidth,
        wallThickness,
        { isStatic: true }
      ),
      Matter.Bodies.rectangle(
        -wallThickness / 2,
        window.innerHeight / 2,
        wallThickness,
        window.innerHeight,
        { isStatic: true }
      ),
      Matter.Bodies.rectangle(
        window.innerWidth + wallThickness / 2,
        window.innerHeight / 2,
        wallThickness,
        window.innerHeight,
        { isStatic: true }
      ),
    ];
    Matter.World.add(engine.world, walls);

    // Create bubbles for each project
    bodies = projects.map((el, i) => {
      el.style.position = "absolute";
      el.style.transition = "none";
      el.style.zIndex = 10;

      // Place in original grid position (relative to viewport)
      const rect = el.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const r = rect.width / 2;

      el.style.left = x - r + "px";
      el.style.top = y - r + "px";

      // Create physics body
      const body = Matter.Bodies.circle(x, y, r, {
        restitution: 0.8,
        friction: 0.01,
        frictionAir: 0.01,
      });
      body.el = el;
      Matter.World.add(engine.world, body);
      return body;
    });

    // Mouse/touch drag
    mouseConstraint = Matter.MouseConstraint.create(engine, {
      element: document.body,
      constraint: { stiffness: 0.2, render: { visible: false } },
    });
    Matter.World.add(engine.world, mouseConstraint);

    // Sync DOM elements with physics bodies
    Matter.Events.on(engine, "afterUpdate", () => {
      bodies.forEach((body) => {
        const r = body.circleRadius;
        body.el.style.left = body.position.x - r + "px";
        body.el.style.top = body.position.y - r + "px";
      });
    });

    // Device orientation / mouse movement for gravity
    window.addEventListener("deviceorientation", handleOrientation);
    window.addEventListener("mousemove", handleMouseMove);

    // Start engine and render
    Matter.Render.run(render);
    runner = Matter.Runner.create();
    Matter.Runner.run(runner, engine);

    // "Explode": apply random outward force
    setTimeout(() => {
      bodies.forEach((body) => {
        const angle = Math.random() * 2 * Math.PI;
        const force = 0.08 + Math.random() * 0.07;
        Matter.Body.applyForce(body, body.position, {
          x: Math.cos(angle) * force,
          y: Math.sin(angle) * force,
        });
      });
    }, 100);

    // Make Matter.js canvas non-interactive so DOM elements stay clickable
    setTimeout(() => {
      if (render.canvas) {
        render.canvas.style.pointerEvents = "none";
      }
    }, 200);
  }

  function stopBubblePhysics() {
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

    // Animate bubbles back to grid positions
    projects.forEach((el, i) => {
      el.style.transition = "all 1s cubic-bezier(0.4,2,0.6,1)";
      const rect = originalRects[i];
      el.style.left = rect.left + "px";
      el.style.top = rect.top + "px";
    });

    setTimeout(() => {
      projects.forEach((el) => {
        el.style.position = "";
        el.style.left = "";
        el.style.top = "";
        el.style.transition = "";
        el.style.zIndex = "";
        el.style.pointerEvents = "";
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
    // gamma: left/right, beta: up/down
    engine.world.gravity.x = event.gamma / 45;
    engine.world.gravity.y = event.beta / 45;
  }

  function handleMouseMove(event) {
    if (!engine) return;
    // Map mouse X/Y to gravity
    const x = (event.clientX / window.innerWidth - 0.5) * 2;
    const y = (event.clientY / window.innerHeight - 0.5) * 2;
    engine.world.gravity.x = x;
    engine.world.gravity.y = y;
  }

  // Store original positions on load and on resize
  window.addEventListener("DOMContentLoaded", storeOriginalPositions);
  window.addEventListener("resize", storeOriginalPositions);

  toggle.addEventListener("change", function () {
    if (toggle.checked) {
      storeOriginalPositions();
      startBubblePhysics();
    } else {
      stopBubblePhysics();
    }
  });
});
