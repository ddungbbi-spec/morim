
(function(){
 const menu=document.getElementById('mobileMenuToggle'),info=document.getElementById('mobileInfoToggle');
 function resetButtons(){menu.setAttribute('aria-expanded',String(document.body.classList.contains('mobileMenuOpen')));info.setAttribute('aria-expanded',String(document.body.classList.contains('mobileInfoOpen')))}
 menu.addEventListener('click',function(e){e.preventDefault();document.body.classList.toggle('mobileMenuOpen');document.body.classList.remove('mobileInfoOpen');resetButtons()});
 info.addEventListener('click',function(e){e.preventDefault();document.body.classList.toggle('mobileInfoOpen');document.body.classList.remove('mobileMenuOpen');resetButtons()});
 document.querySelector('.menu').addEventListener('click',function(e){if(e.target.closest('button')){document.body.classList.remove('mobileMenuOpen');resetButtons()}});
 document.addEventListener('keydown',function(e){if(e.key==='Escape'){document.body.classList.remove('mobileMenuOpen','mobileInfoOpen');resetButtons()}});
})();
