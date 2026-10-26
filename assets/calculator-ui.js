(function(){
 const panel=document.getElementById('profit-calculator');if(!panel)return;
 const form=panel.querySelector('form'),out=panel.querySelector('output');
 document.querySelectorAll('.calculator-toggle').forEach(b=>b.addEventListener('click',()=>{panel.hidden=!panel.hidden;document.querySelectorAll('.calculator-toggle').forEach(x=>x.setAttribute('aria-expanded',String(!panel.hidden)));if(!panel.hidden)panel.scrollIntoView({behavior:'smooth',block:'start'});}));
 panel.querySelector('.calc-close')?.addEventListener('click',()=>{panel.hidden=true;document.querySelectorAll('.calculator-toggle').forEach(b=>b.setAttribute('aria-expanded','false'));document.querySelector('.calculator-toggle')?.focus();});
 if(!form)return;
 const summary=panel.querySelector('.calc-summary');
 const money=v=>new Intl.NumberFormat('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}).format(v);
 form.querySelector('.calc-reset').addEventListener('click',()=>{form.reset();summary.hidden=true;out.textContent='已恢复报告原输入。';});
 form.querySelector('[name=transport]').addEventListener('change',e=>{const sea=e.target.value==='sea',air=e.target.value==='air';form.elements.rate_cny_kg.value=sea?12:air?55:'';form.elements.divisor.value=sea?6000:air?5000:'';});
 form.addEventListener('submit',e=>{
  e.preventDefault();
  try{
   const raw=Object.fromEntries(new FormData(form));const n=k=>raw[k]===''?null:Number(raw[k]);
   const required=['price_usd','unit_cost_cny','quantity','fx','weight_kg','length_cm','width_cm','height_cm','rate_cny_kg','divisor','commission_pct','returns_pct'];
   if(required.some(k=>n(k)===null||!Number.isFinite(n(k))))throw Error('请填写售价、成本、装数、汇率、包装及费用输入。');
   const q=n('quantity'),fx=n('fx'),p=n('price_usd');
   if(!Number.isInteger(q)||q<1||fx<=0||p<=0||n('unit_cost_cny')<0)throw Error('装数须为正整数；售价、汇率须大于0，成本不得为负。');
   if(['commission_pct','returns_pct'].some(k=>n(k)<0||n(k)>100))throw Error('费用比例须在0–100之间。');
   let box={kg:n('weight_kg'),l:n('length_cm'),w:n('width_cm'),h:n('height_cm')};
   if(raw.package_basis==='unit'){box.kg*=q;box.w*=q;}
   const freight=AFPCMath.freight({...box,fx,rate:n('rate_cny_kg'),divisor:n('divisor')});if(!freight)throw Error('包装尺寸、重量和材积重除数须大于0，运费单价不得为负。');
   const special=n('special_usd'),override=n('fba_override_usd');if(special!==null&&(!Number.isFinite(special)||special<0))throw Error('特殊处理费不得为负。');
   const ref=AFPCMath.fba({...box,price:p,peak:raw.season==='peak',fuel:raw.fuel_mode==='on',special});
   if(override!==null&&(!Number.isFinite(override)||override<0||!raw.fba_override_source.trim()))throw Error('覆盖FBA须提供非负金额和来源。');
   const delivery=override===null?ref?.total:override;if(delivery==null)throw Error('请补适用的特殊处理费或有来源的FBA覆盖值。');
   let ads;
   if(raw.advertising_model==='bid_cvr'){
    const bid=n('suggested_bid_usd'),cvr=n('conversion_rate_pct');if(bid===null||!Number.isFinite(bid)||bid<0||cvr===null||!Number.isFinite(cvr)||cvr<=0||cvr>100)throw Error('请填写有效建议竞价与假设转化率。');ads=bid/(cvr/100);
   }else{const pct=n('advertising_pct');if(pct===null||!Number.isFinite(pct)||pct<0||pct>100)throw Error('广告预算须在0–100之间。');ads=p*pct/100;}
   const procurement=n('unit_cost_cny')*(raw.cost_basis==='unit'?q:1)/fx;
   const profit=p-procurement-freight.usd-delivery-p*n('commission_pct')/100-p*n('returns_pct')/100-ads;
   summary.hidden=false;
   const results={freight:money(freight.usd),fba:money(delivery),profit:money(profit),margin:(profit/p*100).toFixed(1)+'%'};
   summary.querySelectorAll('[data-result]').forEach(el=>{el.textContent=results[el.dataset.result];});
   out.textContent='预估利润 $'+money(profit)+' / 利润率 '+(profit/p*100).toFixed(1)+'%\n采购 $'+money(procurement)+' · 头程 $'+money(freight.usd)+' · FBA $'+money(delivery)+' · 广告情景 $'+money(ads)+'\n'+(override===null?ref.name+' · 固定参考费率':'FBA来源：'+raw.fba_override_source);
  }catch(err){summary.hidden=true;out.textContent=err.message;}
 });
})();
