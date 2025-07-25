document.addEventListener('DOMContentLoaded', function() {
  const toggle = document.getElementById('mobile-menu-toggle');
  const menu = document.getElementById('nav-menu');
  
  toggle.addEventListener('click', function() {
    const isExpanded = this.getAttribute('aria-expanded') === 'true';
    this.setAttribute('aria-expanded', !isExpanded);
    menu.classList.toggle('active');
    document.body.classList.toggle('menu-open');
  });
  
  const navLinks = document.querySelectorAll('.nav-menu a');
  navLinks.forEach(link => {
    link.addEventListener('click', function() {
      toggle.setAttribute('aria-expanded', 'false');
      menu.classList.remove('active');
      document.body.classList.remove('menu-open');
    });
  });
});
