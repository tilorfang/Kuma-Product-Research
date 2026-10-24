/* Port of V17 FbaModel.cs / Integration.cs. No network or OCR. */
(function(root) {
  'use strict';
  const ceil = x => Math.ceil(x - 1e-9);
  const up = x => ceil(x * 100) / 100;
  const positive = x => Number.isFinite(x) && x > 0;
  const nonnegative = x => Number.isFinite(x) && x >= 0;
  const smallOff = [[2.43,3.32,3.58],[2.49,3.42,3.68],[2.56,3.45,3.71],[2.66,3.54,3.80],[2.77,3.68,3.94],[2.82,3.78,4.04],[2.92,3.91,4.17],[2.95,3.96,4.22]];
  const smallPeak = [[2.62,3.51,3.77],[2.68,3.61,3.87],[2.76,3.65,3.91],[2.86,3.74,4],[2.98,3.89,4.15],[3.03,3.99,4.25],[3.14,4.13,4.39],[3.17,4.18,4.44]];
  const largeOff = [[2.91,3.73,3.99],[3.13,3.95,4.21],[3.38,4.20,4.46],[3.78,4.60,4.86],[4.22,5.04,5.30],[4.60,5.42,5.68],[4.75,5.57,5.83],[5,5.82,6.08],[5.10,5.92,6.18],[5.28,6.10,6.36],[5.44,6.26,6.52],[5.85,6.67,6.93]];
  const largePeak = [[3.15,3.97,4.23],[3.39,4.21,4.47],[3.66,4.48,4.74],[4.07,4.89,5.15],[4.52,5.34,5.60],[4.91,5.73,5.99],[5.07,5.89,6.15],[5.33,6.15,6.41],[5.47,6.29,6.55],[5.67,6.49,6.75],[5.84,6.66,6.92],[6.26,7.08,7.34]];
  const names = ['小号标准尺寸','大号标准尺寸','小号大件','大号大件','超大件 0–50 磅','超大件 50–70 磅','超大件 70–150 磅','超大件超过 150 磅'];
  function fba({kg,l,w,h,price,peak=false,fuel=true,special=null}) {
    if (![kg,l,w,h,price].every(positive) || (special!==null&&!nonnegative(special))) return null;
    const [s,m,long] = [l/2.54,w/2.54,h/2.54].sort((a,b)=>a-b);
    const actual=kg/.45359237, girth=long+2*(m+s);
    const small=long<=15+1e-10&&m<=12+1e-10&&s<=.75+1e-10&&actual<=1+1e-10;
    const dim=small?long*m*s/139:long*Math.max(m,2)*Math.max(s,2)/139;
    const shipping=Math.max(actual,dim);
    let tier;
    if(small) tier=0;
    else if(long<=18+1e-10&&m<=14+1e-10&&s<=8+1e-10&&shipping<=20+1e-10) tier=1;
    else if(long<=37+1e-10&&m<=28+1e-10&&s<=20+1e-10&&girth<=130+1e-10&&shipping<=50+1e-10) tier=2;
    else if(long<=59+1e-10&&m<=33+1e-10&&s<=33+1e-10&&girth<=130+1e-10&&shipping<=50+1e-10) tier=3;
    else tier=shipping<=50+1e-10?4:shipping<=70+1e-10?5:shipping<=150+1e-10?6:7;
    const band=price<10?0:price<=50?1:2;
    let charge,base;
    if(tier===0) { charge=ceil(actual*8)/8; base=(peak?smallPeak:smallOff)[Math.max(0,charge*8-1)][band]; }
    else if(tier===1) {
      charge=ceil(shipping*4)/4;
      base=charge<=3?(peak?largePeak:largeOff)[Math.max(0,charge*4-1)][band]:(peak?[6.69,7.51,7.77]:[6.15,6.97,7.23])[band]+(charge-3)*4*.08;
    } else {
      charge=ceil(tier===7?actual:shipping);
      const pick=(a,b,c,d)=>peak?(band===0?c:d):(band===0?a:b);
      if(tier===2) base=pick(6.78,7.55,7.82,8.59)+Math.max(0,charge-1)*.38;
      if(tier===3) base=pick(8.58,9.35,9.62,10.39)+Math.max(0,charge-1)*.38;
      if(tier===4) base=pick(25.56,26.33,28.29,29.06)+Math.max(0,charge-1)*.38;
      if(tier===5) base=pick(36.55,37.32,39.36,40.13)+Math.max(0,charge-51)*.75;
      if(tier===6) base=pick(50.55,51.32,54.97,55.74)+Math.max(0,charge-71)*.75;
      if(tier===7) base=pick(194.18,194.95,202.69,203.46)+Math.max(0,charge-151)*.19;
    }
    const needsSpecial=tier>=4&&tier<=6&&(long>96+1e-10||girth>130+1e-10);
    const fuelFee=fuel?base*.035:0;
    return {tier,name:names[tier],actual,dim,charge,base,fuelFee,needsSpecial,total:needsSpecial&&special===null?null:up(base+fuelFee+(needsSpecial?up(special):0))};
  }
  function freight({kg,l,w,h,divisor,rate,fx}) {
    if(![kg,l,w,h,divisor,fx].every(positive)||!nonnegative(rate)) return null;
    const volume=l*w*h/divisor, bill=Math.max(kg,volume), cny=bill*rate;
    return {volume,bill,cny,usd:up(cny/fx)};
  }
  function profit({price,cost,quantity=1,fx,freight,delivery,commission=15,advertising=20,returns=5}) {
    if(!positive(fx)||!Number.isInteger(quantity)||quantity<1||![price,cost,freight,delivery,commission,advertising,returns].every(nonnegative))return null;
    const costUsd=cost*quantity/fx, fees=price*(commission+advertising+returns)/100;
    const total=costUsd+freight+delivery+fees;
    return {costUsd,total,profit:price-total,margin:price===0?null:(price-total)/price,commission:price*commission/100,advertising:price*advertising/100,returns:price*returns/100};
  }
  function packPrice(price,n) { return n===1?price:n===2?up(price*2*.9):n===3?up(price*3*.8):null; }
  const api={ceil,up,fba,freight,profit,packPrice};
  root.AFPCMath=api;
  if(typeof module!=='undefined') module.exports=api;
})(globalThis);
