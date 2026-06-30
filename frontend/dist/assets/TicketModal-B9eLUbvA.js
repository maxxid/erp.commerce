import{k as a,h as u,c as l,d as t,f as x,q as g,t as n,F as h,m as w,g as r,v as y,L as k,j as p}from"./index-CVGP01y5.js";const v={class:"bg-white rounded-2xl shadow-2xl max-w-sm w-full max-h-[90vh] overflow-y-auto"},j={class:"flex items-center justify-between p-4 border-b border-slate-100"},_={class:"flex items-center gap-2"},T={class:"text-center border-b-2 border-slate-900 pb-2 mb-2"},C={class:"text-[9px] text-slate-500"},z={class:"text-[9px] text-slate-400"},$={class:"font-bold text-sm mt-1"},F={class:"space-y-0.5 mb-2"},N={class:"flex-1 truncate"},S={key:0,class:"text-[9px] text-orange-600 font-bold"},B={class:"w-10 text-right"},E={class:"w-20 text-right font-mono-data"},O={class:"w-20 text-right font-bold"},L={class:"border-t border-slate-300 pt-1 space-y-0.5"},P={key:0,class:"flex justify-between text-[10px]"},D={class:"font-bold"},I={class:"flex justify-between text-sm font-bold"},M={class:"border-t border-dotted border-slate-300 mt-2 pt-1 text-[10px] space-y-0.5"},V={class:"flex justify-between"},A={class:"font-bold capitalize"},W={key:0,class:"flex justify-between"},R={class:"font-bold"},q={key:0,class:"border-t border-dotted border-slate-300 mt-2 pt-1 text-[9px] space-y-0.5"},G={class:"flex justify-between"},H={class:"font-bold"},J={class:"text-center text-[8px] text-slate-400 mt-3 pt-2 border-t border-slate-200"},U={__name:"TicketModal",props:{show:Boolean,ticket:{type:Object,default:()=>({items:[]})}},emits:["close"],setup(o){const d=p(()=>{try{const i=JSON.parse(localStorage.getItem("apex_lookup_settings"));return(i==null?void 0:i.ticketWidth)||80}catch{return 80}}),m=p(()=>({width:"100%",maxWidth:d.value+"mm",margin:"0 auto",fontFamily:"'Courier New', monospace"}));function c(i){return i==null?"$0":"$"+Number(i).toLocaleString("es-AR",{minimumFractionDigits:2})}function b(){const i=document.getElementById("thermal-ticket");if(!i)return;const e=window.open("","_blank","width=300,height=600");e.document.write(`
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Ticket</title>
    <style>
      * { margin:0; padding:0; box-sizing:border-box; }
      body {
        font-family:'Courier New',monospace;
        font-size:11px;
        width:${d.value}mm;
        margin:0 auto;
        padding:4mm;
        color:#000;
        background:#fff;
      }
      .text-center { text-align:center; }
      .border-b-2 { border-bottom:2px solid #000; }
      .border-b { border-bottom:1px dashed #999; }
      .border-dotted { border-bottom:1px dotted #999; }
      .border-t { border-top:1px solid #999; }
      .border-t-2 { border-top:2px solid #000; }
      .pb-2 { padding-bottom:2px; }
      .mb-2 { margin-bottom:2px; }
      .mt-1 { margin-top:1px; }
      .mt-2 { margin-top:2px; }
      .mt-3 { margin-top:3px; }
      .pt-1 { padding-top:1px; }
      .pt-2 { padding-top:2px; }
      .space-y-0\\.5 > * + * { margin-top:0.5px; }
      .flex { display:flex; }
      .flex-col { flex-direction:column; }
      .items-center { align-items:center; }
      .justify-between { justify-content:space-between; }
      .font-bold { font-weight:bold; }
      .text-\\[9px\\] { font-size:9px; }
      .text-\\[10px\\] { font-size:10px; }
      .text-\\[11px\\] { font-size:11px; }
      .text-\\[8px\\] { font-size:8px; }
      .text-sm { font-size:11px; }
      .text-orange-600 { color:#ea580c; }
      .text-slate-400 { color:#94a3b8; }
      .text-slate-500 { color:#64748b; }
      .text-slate-900 { color:#0f172a; }
      .w-10 { width:10mm; }
      .w-20 { width:20mm; }
      .flex-1 { flex:1; }
      .truncate { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .text-right { text-align:right; }
      .font-mono { font-family:'Courier New',monospace; }
      .font-mono-data { font-family:'Courier New',monospace; }
      .pb-0\\.5 { padding-bottom:0.5px; }
      @page { size:${d.value}mm auto; margin:0; }
      @media print {
        body { width:${d.value}mm; }
        button { display:none; }
      }
    </style></head><body>${i.innerHTML}</body></html>
  `),e.document.close(),setTimeout(()=>e.print(),300)}return(i,e)=>(a(),u(k,{to:"body"},[o.show?(a(),l("div",{key:0,class:"fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm",onClick:e[1]||(e[1]=y(s=>i.$emit("close"),["self"]))},[t("div",v,[t("div",j,[e[4]||(e[4]=t("h3",{class:"font-bold text-slate-900 text-sm"},"Ticket de Venta",-1)),t("div",_,[t("button",{onClick:b,class:"px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1"},[...e[2]||(e[2]=[t("i",{class:"fa-solid fa-print"},null,-1),x(" Imprimir ",-1)])]),t("button",{onClick:e[0]||(e[0]=s=>i.$emit("close")),class:"w-7 h-7 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition"},[...e[3]||(e[3]=[t("i",{class:"fa-solid fa-xmark text-xs"},null,-1)])])])]),t("div",{id:"thermal-ticket",class:"p-4 font-mono text-[11px] leading-snug text-slate-900",style:g(m.value)},[t("div",T,[e[5]||(e[5]=t("p",{class:"font-bold text-sm"},"ApexERP",-1)),t("p",C,n(o.ticket.sucursal||"Sucursal Principal"),1),t("p",z,n(o.ticket.fecha),1),t("p",$,"TICKET #"+n(o.ticket.numero),1)]),t("div",F,[e[6]||(e[6]=t("div",{class:"flex justify-between text-[9px] font-bold text-slate-400 border-b border-dotted border-slate-300 pb-0.5"},[t("span",{class:"flex-1"},"Producto"),t("span",{class:"w-10 text-right"},"Cant"),t("span",{class:"w-20 text-right"},"Precio"),t("span",{class:"w-20 text-right"},"Subtotal")],-1)),(a(!0),l(h,null,w(o.ticket.items,(s,f)=>(a(),l("div",{key:f,class:"flex justify-between text-[10px]"},[t("span",N,[x(n(s.nombre)+" ",1),s.oferta?(a(),l("span",S,"["+n(s.oferta.tipo==="porcentaje"?s.oferta.valor+"% OFF":s.oferta.tipo==="monto_fijo"?"$"+s.oferta.valor+" OFF":"2x1")+"]",1)):r("",!0)]),t("span",B,n(s.cantidad),1),t("span",E,n(c(s._precio_neto||s.precio_unitario)),1),t("span",O,n(c((s._precio_neto||s.precio_unitario)*s.cantidad)),1)]))),128))]),t("div",L,[o.ticket.descuento?(a(),l("div",P,[e[7]||(e[7]=t("span",null,"Descuento",-1)),t("span",D,"- "+n(c(o.ticket.descuento)),1)])):r("",!0),t("div",I,[e[8]||(e[8]=t("span",null,"TOTAL",-1)),t("span",null,n(c(o.ticket.total)),1)])]),t("div",M,[t("div",V,[e[9]||(e[9]=t("span",null,"Medio de pago",-1)),t("span",A,n(o.ticket.medio_pago),1)]),o.ticket.cliente?(a(),l("div",W,[e[10]||(e[10]=t("span",null,"Cliente",-1)),t("span",R,n(o.ticket.cliente),1)])):r("",!0)]),o.ticket.factura?(a(),l("div",q,[t("div",G,[e[11]||(e[11]=t("span",null,"Factura Electrónica",-1)),t("span",H,n(o.ticket.factura),1)])])):r("",!0),t("div",J,[e[12]||(e[12]=t("p",null,"Gracias por su compra",-1)),t("p",null,n(o.ticket.fecha),1)])],4)])])):r("",!0)]))}};export{U as _};
