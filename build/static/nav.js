document.addEventListener('DOMContentLoaded', function() {
  const menuToggle = document.getElementById('mobile-menu-toggle');
  const navMenu = document.getElementById('nav-menu');
  const body = document.body;
  const hamburger = menuToggle.querySelector('.hamburger');
  const closeIcon = menuToggle.querySelector('.close-icon');

  // Debugging check
  console.log('Menu elements loaded:', {menuToggle, navMenu});

  if (!menuToggle || !navMenu) {
    console.error('Critical elements missing for mobile menu');
    return;
  }

  menuToggle.addEventListener('click', function() {
    // Toggle menu visibility
    navMenu.classList.toggle('active');
    menuToggle.classList.toggle('active');
    body.classList.toggle('menu-open');
    
    // Toggle icons
    hamburger.classList.toggle('hidden');
    closeIcon.classList.toggle('hidden');
    
    // Update aria-expanded
    const isExpanded = this.getAttribute('aria-expanded') === 'true';
    this.setAttribute('aria-expanded', !isExpanded);
    
    console.log('Menu toggled. Active:', navMenu.classList.contains('active'));
  });

  // Close menu when clicking links
  document.querySelectorAll('.nav-menu a').forEach(link => {
    link.addEventListener('click', function() {
      navMenu.classList.remove('active');
      menuToggle.classList.remove('active');
      body.classList.remove('menu-open');
      hamburger.classList.remove('hidden');
      closeIcon.classList.add('hidden');
      menuToggle.setAttribute('aria-expanded', 'false');
    });
  });
});
