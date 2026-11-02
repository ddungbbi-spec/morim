(function(){
 'use strict';
 const menu=document.getElementById('mobileMenuToggle');
 const info=document.getElementById('mobileInfoToggle');
 const menuPanel=document.querySelector('.menu');
 if(!menu||!info||!menuPanel)return;
 const isOpen=type=>document.body.classList.contains(type);
 function sync(){
   menu.setAttribute('aria-expanded',String(isOpen('mobileMenuOpen')));
   info.setAttribute('aria-expanded',String(isOpen('mobileInfoOpen')));
   menu.setAttribute('aria-label',isOpen('mobileMenuOpen')?'메뉴 닫기':'메뉴 열기');
   info.setAttribute('aria-label',isOpen('mobileInfoOpen')?'상태 닫기':'상태 열기');
 }
 function close(){document.body.classList.remove('mobileMenuOpen','mobileInfoOpen');sync()}
 function toggle(name){
   const wasOpen=isOpen(name);
   close();
   if(!wasOpen)document.body.classList.add(name);
   sync();
 }
 menu.addEventListener('click',e=>{e.preventDefault();toggle('mobileMenuOpen')});
 info.addEventListener('click',e=>{e.preventDefault();toggle('mobileInfoOpen')});
 menuPanel.addEventListener('click',e=>{if(e.target.closest('button'))close()});
 document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
 document.addEventListener('pointerdown',e=>{
   if(!isOpen('mobileMenuOpen')&&!isOpen('mobileInfoOpen'))return;
   if(e.target.closest('.mobileTools,.menu,.quest,.extra,.overlay'))return;
   close();
 });
 window.addEventListener('resize',()=>{
   if(window.matchMedia('(min-width: 851px) and (pointer: fine)').matches)close();
 });
 sync();
})();
