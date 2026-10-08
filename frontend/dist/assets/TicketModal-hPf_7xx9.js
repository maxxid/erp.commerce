import{m as l,h as g,c as a,d as t,f as p,g as r,z as h,t as i,F as k,q as w,i as y,L as v,l as x}from"./index-DjweEGob.js";const _={class:"bg-white rounded-2xl shadow-2xl max-w-sm w-full max-h-[90vh] overflow-y-auto"},j={class:"flex items-center justify-between p-4 border-b border-slate-100"},T={class:"flex items-center gap-2"},C={class:"text-center border-b-2 border-slate-900 pb-2 mb-2"},$={class:"text-[9px] text-slate-500"},z={class:"text-[9px] text-slate-400"},F={class:"font-bold text-sm mt-1"},S={class:"space-y-0.5 mb-2"},N={class:"flex-1 truncate"},E={key:0,class:"text-[9px] text-orange-600 font-bold"},B={class:"w-10 text-right"},O={class:"w-20 text-right font-mono-data"},L={class:"w-20 text-right font-bold"},P={class:"border-t border-slate-300 pt-1 space-y-0.5"},D={key:0,class:"flex justify-between text-[10px]"},I={class:"font-bold"},M={class:"flex justify-between text-sm font-bold"},V={class:"border-t border-dotted border-slate-300 mt-2 pt-1 text-[10px] space-y-0.5"},A={class:"flex justify-between"},W={class:"font-bold capitalize"},R={key:0,class:"flex justify-between"},q={class:"font-bold"},G={key:0,class:"border-t border-dotted border-slate-300 mt-2 pt-1 text-[9px] space-y-0.5"},H={class:"flex justify-between"},J={class:"font-bold"},K={class:"text-center text-[8px] text-slate-400 mt-3 pt-2 border-t border-slate-200"},Y={__name:"TicketModal",props:{show:Boolean,ticket:{type:Object,default:()=>({items:[]})}},emits:["close","emitir-factura"],setup(n){function u(o){return o.subtotal!=null?o.subtotal:o.por_kilo?o._importe!=null&&o._importe>0?o._importe:(o.precio_unitario||0)*(o.peso||0):(o._precio_neto||o.precio_unitario||0)*(o.cantidad||0)}const d=x(()=>{try{const o=JSON.parse(localStorage.getItem("apex_lookup_settings"));return(o==null?void 0:o.ticketWidth)||80}catch{return 80}}),f=x(()=>({width:"100%",maxWidth:d.value+"mm",margin:"0 auto",fontFamily:"'Courier New', monospace"}));function c(o){return o==null?"$0":"$"+Number(o).toLocaleString("es-AR",{minimumFractionDigits:2})}function b(){const o=document.getElementById("thermal-ticket");if(!o)return;const e=window.open("","_blank","width=300,height=600");e.document.write(`
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
    </style></head><body>${o.innerHTML}</body></html>
  `),e.document.close(),setTimeout(()=>e.print(),300)}return(o,e)=>(l(),g(v,{to:"body"},[n.show?(l(),a("div",{key:0,class:"fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm",onClick:e[2]||(e[2]=y(s=>o.$emit("close"),["self"]))},[t("div",_,[t("div",j,[e[6]||(e[6]=t("h3",{class:"font-bold text-slate-900 text-sm"},"Ticket de Venta",-1)),t("div",T,[n.ticket.venta_id?(l(),a("button",{key:0,onClick:e[0]||(e[0]=s=>o.$emit("emitir-factura",n.ticket.venta_id)),class:"px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1"},[...e[3]||(e[3]=[t("i",{class:"fa-solid fa-file-invoice"},null,-1),p(" FE ",-1)])])):r("",!0),t("button",{onClick:b,class:"px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1"},[...e[4]||(e[4]=[t("i",{class:"fa-solid fa-print"},null,-1),p(" Imprimir ",-1)])]),t("button",{onClick:e[1]||(e[1]=s=>o.$emit("close")),class:"w-7 h-7 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition"},[...e[5]||(e[5]=[t("i",{class:"fa-solid fa-xmark text-xs"},null,-1)])])])]),t("div",{id:"thermal-ticket",class:"p-4 font-mono text-[11px] leading-snug text-slate-900",style:h(f.value)},[t("div",C,[e[7]||(e[7]=t("p",{class:"font-bold text-sm"},"ApexERP",-1)),t("p",$,i(n.ticket.sucursal||"Sucursal Principal"),1),t("p",z,i(n.ticket.fecha),1),t("p",F,"TICKET #"+i(n.ticket.numero),1)]),t("div",S,[e[8]||(e[8]=t("div",{class:"flex justify-between text-[9px] font-bold text-slate-400 border-b border-dotted border-slate-300 pb-0.5"},[t("span",{class:"flex-1"},"Producto"),t("span",{class:"w-10 text-right"},"Cant"),t("span",{class:"w-20 text-right"},"Precio"),t("span",{class:"w-20 text-right"},"Subtotal")],-1)),(l(!0),a(k,null,w(n.ticket.items,(s,m)=>(l(),a("div",{key:m,class:"flex justify-between text-[10px]"},[t("span",N,[p(i(s.nombre)+" ",1),s.oferta?(l(),a("span",E,"["+i(s.oferta.tipo==="porcentaje"?s.oferta.valor+"% OFF":s.oferta.tipo==="monto_fijo"?"$"+s.oferta.valor+" OFF":"2x1")+"]",1)):r("",!0)]),t("span",B,i(s.por_kilo?(s.peso||0)+" kg":s.cantidad),1),t("span",O,i(c(s.por_kilo?s.precio_unitario:s._precio_neto||s.precio_unitario)),1),t("span",L,i(c(u(s))),1)]))),128))]),t("div",P,[n.ticket.descuento?(l(),a("div",D,[e[9]||(e[9]=t("span",null,"Descuento",-1)),t("span",I,"- "+i(c(n.ticket.descuento)),1)])):r("",!0),t("div",M,[e[10]||(e[10]=t("span",null,"TOTAL",-1)),t("span",null,i(c(n.ticket.total)),1)])]),t("div",V,[t("div",A,[e[11]||(e[11]=t("span",null,"Medio de pago",-1)),t("span",W,i(n.ticket.medio_pago),1)]),n.ticket.cliente?(l(),a("div",R,[e[12]||(e[12]=t("span",null,"Cliente",-1)),t("span",q,i(n.ticket.cliente),1)])):r("",!0)]),n.ticket.factura?(l(),a("div",G,[t("div",H,[e[13]||(e[13]=t("span",null,"Factura Electrónica",-1)),t("span",J,i(n.ticket.factura),1)])])):r("",!0),t("div",K,[e[14]||(e[14]=t("p",null,"Gracias por su compra",-1)),t("p",null,i(n.ticket.fecha),1)])],4)])])):r("",!0)]))}};export{Y as _};
