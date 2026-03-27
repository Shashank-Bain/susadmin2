function openModal(id){const el=document.getElementById(id);if(el)el.classList.add("open")}
function closeModal(id){const el=document.getElementById(id);if(el)el.classList.remove("open")}
function toggleDropdown(id){document.querySelectorAll(".dropdown-card.open").forEach(el=>{if(el.id!==id)el.classList.remove("open")});const el=document.getElementById(id);if(el)el.classList.toggle("open")}
function closeDropdown(id){const el=document.getElementById(id);if(el)el.classList.remove("open")}
document.addEventListener("click",(e)=>{if(!e.target.closest(".dropdown-shell")&&!e.target.closest(".topbar-user-menu")){document.querySelectorAll(".dropdown-card.open").forEach(el=>el.classList.remove("open"))}})
function todayString(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function getProjectMetaByName(name){const config=window.staffingConfig||{projects:[]};return config.projects.find(p=>p.project_name===name)||null}
function getEmployeeIdByName(name){const config=window.staffingConfig||{employees:[]};const item=config.employees.find(e=>e.name===name);return item?item.id:""}
function staffingTypeOptionsHtml(selected){const opts=(window.staffingConfig?.staffingTypes||[]);return opts.map(v=>`<option value="${v}" ${selected===v?"selected":""}>${v}</option>`).join("")}
function createStaffingRow(data={}){
  const tr=document.createElement("tr");
  tr.innerHTML=`
    <td><input class="glass-input table-input" list="employee-options" value="${data.employee_name||""}" placeholder="Type employee name" /></td>
    <td><select class="glass-input table-input staffing-type-select">${staffingTypeOptionsHtml(data.staffing_type||"")}</select></td>
    <td><input class="glass-input table-input project-input" list="project-options" value="${data.project_name||""}" placeholder="Type project name" /></td>
    <td><input class="glass-input table-input case-code-input" value="${data.case_code||""}" /></td>
    <td><input class="glass-input table-input hours-input" type="number" step="0.5" value="${data.hours||8}" /></td>
    <td><input class="glass-input table-input" value="${data.comments||""}" /></td>
    <td><button class="icon-btn danger" type="button">×</button></td>`;
  tr.querySelector(".danger").addEventListener("click",()=>{tr.remove();deriveBilling()});
  const projectInput=tr.querySelector(".project-input");
  projectInput.addEventListener("change",()=>{const meta=getProjectMetaByName(projectInput.value);if(meta){tr.querySelector(".case-code-input").value=meta.billing_case_code||"";tr.dataset.projectId=meta.id||"";tr.dataset.teamId=meta.team_id||""}else{tr.dataset.projectId="";tr.dataset.teamId=""}deriveBilling()});
  tr.querySelectorAll("input,select").forEach(inp=>{inp.addEventListener("change",deriveBilling);inp.addEventListener("keyup",deriveBilling)});
  const meta=getProjectMetaByName(data.project_name||"");tr.dataset.projectId=data.project_id||(meta?meta.id:"");tr.dataset.teamId=data.team_id||(meta?meta.team_id:"");return tr
}
function staffingRowsPayload(){
  const rows=[];document.querySelectorAll("#staffing-table-body tr").forEach(tr=>{
    const employeeName=tr.querySelectorAll("input")[0].value.trim();
    const staffingType=tr.querySelector(".staffing-type-select").value.trim();
    const inputEls=tr.querySelectorAll("input");
    const projectName=inputEls[1].value.trim();
    const caseCode=inputEls[2].value.trim();
    const hours=parseFloat(inputEls[3].value||"0");
    const comments=inputEls[4].value.trim();
    const projectMeta=getProjectMetaByName(projectName);
    rows.push({employee_id:getEmployeeIdByName(employeeName),employee_name:employeeName,staffing_type:staffingType,project_id:projectMeta?projectMeta.id:(tr.dataset.projectId||""),team_id:projectMeta?projectMeta.team_id:(tr.dataset.teamId||""),project_name:projectName,case_code:caseCode,hours:hours,comments:comments})
  });return rows.filter(r=>r.employee_name||r.project_name||r.staffing_type||r.case_code)
}
function renderBillingRows(rows){const tbody=document.getElementById("billing-table-body");if(!tbody)return;tbody.innerHTML="";rows.forEach((row)=>{const tr=document.createElement("tr");tr.innerHTML=`<td>${row.project_name||""}</td><td>${row.project_type||""}</td><td>${row.case_code||""}</td><td><input class="glass-input table-input" type="number" step="0.01" value="${row.billable_ftes||0}" /></td><td><input class="glass-input table-input" type="number" step="0.01" value="${row.billing_amount||0}" /></td><td><input class="glass-input table-input" value="${row.comments||""}" /></td>`;tr.dataset.projectId=row.project_id||"";tr.dataset.projectName=row.project_name||"";tr.dataset.projectType=row.project_type||"";tr.dataset.caseCode=row.case_code||"";tbody.appendChild(tr)})}
function billingRowsPayload(){const rows=[];document.querySelectorAll("#billing-table-body tr").forEach(tr=>{const inputs=tr.querySelectorAll("input");rows.push({project_id:tr.dataset.projectId||"",project_name:tr.dataset.projectName||"",project_type:tr.dataset.projectType||"",case_code:tr.dataset.caseCode||"",billable_ftes:parseFloat(inputs[0].value||"0"),billing_amount:parseFloat(inputs[1].value||"0"),comments:inputs[2].value.trim()})});return rows}
async function deriveBilling(){const rows=staffingRowsPayload();const res=await fetch("/api/staffing/derive-billing",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({rows})});const data=await res.json();renderBillingRows(data.billing_rows||[])}
function addStaffingRow(data={}){const tbody=document.getElementById("staffing-table-body");if(tbody)tbody.appendChild(createStaffingRow(data))}
function clearStaffingRows(){const tbody=document.getElementById("staffing-table-body");const billing=document.getElementById("billing-table-body");if(tbody)tbody.innerHTML="";if(billing)billing.innerHTML=""}
async function loadStaffingPrefill(customDate=""){const dateInput=document.getElementById("staffing-date");if(dateInput&&!dateInput.value)dateInput.value=todayString();const date=dateInput?dateInput.value:todayString();let url=`/api/staffing/prefill?date=${encodeURIComponent(date)}`;if(customDate)url+=`&load_date=${encodeURIComponent(customDate)}`;const res=await fetch(url);const data=await res.json();const label=document.getElementById("prefill-date-label");if(label)label.textContent=data.source_date||"—";clearStaffingRows();const rows=data.rows||[];if(rows.length===0){addStaffingRow();renderBillingRows([]);return}rows.forEach(r=>addStaffingRow(r));renderBillingRows(data.billing_rows||[])}
function loadFromCustomDate(){const input=document.getElementById("load-date");if(input&&input.value){loadStaffingPrefill(input.value);closeModal("load-modal")}}
async function saveStaffingRows(){
  const date=document.getElementById("staffing-date").value||todayString();
  const rows=staffingRowsPayload();
  const billingRows=billingRowsPayload();
  
  try{
    const res=await fetch("/api/staffing/save",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({date,rows,billing_rows:billingRows})
    });
    const data=await res.json();
    
    // Show success message without blocking
    showStaffingStatus(data.message||"Saved successfully!",data.ok?"success":"error");
  }catch(err){
    showStaffingStatus("Error saving data","error");
  }
}

function doneStaffingEntry(){
  closeModal("staffing-modal");
  window.location.reload();
}

function showStaffingStatus(message,type="success"){
  // Create or update status message
  let statusEl=document.getElementById("staffing-status");
  if(!statusEl){
    statusEl=document.createElement("div");
    statusEl.id="staffing-status";
    statusEl.style.cssText="position:fixed;top:80px;right:20px;padding:12px 20px;border-radius:8px;font-weight:500;z-index:10000;transition:opacity 0.3s;";
    document.body.appendChild(statusEl);
  }
  
  statusEl.textContent=message;
  statusEl.style.background=type==="success"?"rgba(100,200,100,0.9)":"rgba(255,100,100,0.9)";
  statusEl.style.color="#fff";
  statusEl.style.opacity="1";
  
  // Auto-hide after 3 seconds
  setTimeout(()=>{
    statusEl.style.opacity="0";
  },3000);
}

async function submitProjectForm(event){event.preventDefault();const formData=new FormData(event.target);const res=await fetch("/api/projects/create",{method:"POST",body:formData});const data=await res.json();if(data.ok){alert("Project added. Refresh the page to see it in the current projects list.");event.target.reset()}else{alert(data.message||"Unable to add project")}}

/* Save Multiple Dates Functions */
let calendarCurrentDate=new Date();
let selectedDates=new Set();

function openSaveMultipleModal(){
  calendarCurrentDate=new Date();
  selectedDates.clear();
  renderCalendar();
  openModal("save-multiple-modal");
}

function changeCalendarMonth(offset){
  calendarCurrentDate.setMonth(calendarCurrentDate.getMonth()+offset);
  renderCalendar();
}

function renderCalendar(){
  const year=calendarCurrentDate.getFullYear();
  const month=calendarCurrentDate.getMonth();
  
  // Update month/year display
  const monthNames=["January","February","March","April","May","June","July","August","September","October","November","December"];
  const monthYearEl=document.getElementById("calendar-month-year");
  if(monthYearEl){
    monthYearEl.textContent=`${monthNames[month]} ${year}`;
  }
  
  // Get first day of month and number of days
  const firstDay=new Date(year,month,1);
  const lastDay=new Date(year,month+1,0);
  const daysInMonth=lastDay.getDate();
  const startingDayOfWeek=firstDay.getDay();
  
  // Build calendar HTML
  let html=`
    <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 8px;">
      <div style="text-align: center; font-weight: 600; font-size: 12px; padding: 8px; opacity: 0.6;">Sun</div>
      <div style="text-align: center; font-weight: 600; font-size: 12px; padding: 8px; opacity: 0.6;">Mon</div>
      <div style="text-align: center; font-weight: 600; font-size: 12px; padding: 8px; opacity: 0.6;">Tue</div>
      <div style="text-align: center; font-weight: 600; font-size: 12px; padding: 8px; opacity: 0.6;">Wed</div>
      <div style="text-align: center; font-weight: 600; font-size: 12px; padding: 8px; opacity: 0.6;">Thu</div>
      <div style="text-align: center; font-weight: 600; font-size: 12px; padding: 8px; opacity: 0.6;">Fri</div>
      <div style="text-align: center; font-weight: 600; font-size: 12px; padding: 8px; opacity: 0.6;">Sat</div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;">
  `;
  
  // Add empty cells for days before month starts
  for(let i=0;i<startingDayOfWeek;i++){
    html+=`<div></div>`;
  }
  
  // Add days of the month
  const today=new Date();
  today.setHours(0,0,0,0);
  
  for(let day=1;day<=daysInMonth;day++){
    const date=new Date(year,month,day);
    // Format date as YYYY-MM-DD without timezone conversion
    const dateStr=`${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
    const dayOfWeek=date.getDay();
    const isWeekend=dayOfWeek===0||dayOfWeek===6;
    const isToday=date.getTime()===today.getTime();
    const isSelected=selectedDates.has(dateStr);
    
    let bgColor="transparent";
    let borderColor="rgba(255,255,255,0.15)";
    let cursor="pointer";
    
    if(isSelected){
      bgColor="rgba(100,150,255,0.3)";
      borderColor="#6495ff";
    }else if(isToday){
      borderColor="rgba(100,150,255,0.5)";
    }
    
    html+=`
      <div onclick="toggleDateSelection('${dateStr}')" 
           style="
             aspect-ratio: 1;
             display: flex;
             align-items: center;
             justify-content: center;
             background: ${bgColor};
             border: 2px solid ${borderColor};
             border-radius: 8px;
             cursor: ${cursor};
             font-weight: ${isToday?"600":"400"};
             font-size: 13px;
             transition: all 0.2s;
             position: relative;
           "
           onmouseover="this.style.transform='scale(1.05)';this.style.borderColor='#6495ff'"
           onmouseout="this.style.transform='scale(1)';this.style.borderColor='${isSelected?"#6495ff":isToday?"rgba(100,150,255,0.5)":"rgba(255,255,255,0.15)"}'">
        ${day}
      </div>
    `;
  }
  
  html+=`</div>`;
  
  const container=document.getElementById("calendar-container");
  if(container){
    container.innerHTML=html;
  }
  
  updateSelectedCount();
}

function toggleDateSelection(dateStr){
  if(selectedDates.has(dateStr)){
    selectedDates.delete(dateStr);
  }else{
    selectedDates.add(dateStr);
  }
  renderCalendar();
}

function updateSelectedCount(){
  const countEl=document.getElementById("selected-dates-count");
  if(countEl){
    countEl.textContent=selectedDates.size;
  }
}

async function saveToMultipleDates(){
  if(selectedDates.size===0){
    showStaffingStatus("Please select at least one date from the calendar.","error");
    return;
  }
  
  const saveMode=document.querySelector('input[name="save-mode"]:checked').value;
  const rows=staffingRowsPayload();
  const billingRows=billingRowsPayload();
  
  if(rows.length===0){
    showStaffingStatus("No staffing rows to save.","error");
    return;
  }
  
  const confirmMsg=saveMode==="replace"
    ?`This will REPLACE all existing entries for ${selectedDates.size} selected date(s). Continue?`
    :`This will ADD these entries to existing data for ${selectedDates.size} selected date(s). Continue?`;
  
  if(!confirm(confirmMsg))return;
  
  try{
    const res=await fetch("/api/staffing/save-multiple",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({dates:Array.from(selectedDates),rows,billing_rows:billingRows,mode:saveMode})
    });
    
    const data=await res.json();
    
    if(data.ok){
      showStaffingStatus(data.message||`Saved to ${selectedDates.size} date(s) successfully!`,"success");
      closeModal("save-multiple-modal");
      // Clear selections after successful save
      selectedDates.clear();
      renderCalendar();
    }else{
      showStaffingStatus(data.message||"Error saving to multiple dates","error");
    }
  }catch(err){
    console.error(err);
    showStaffingStatus("Error saving to multiple dates","error");
  }
}

function showReportTab(id,btn){document.querySelectorAll(".report-tab").forEach(el=>el.classList.remove("active"));document.querySelectorAll(".tab").forEach(el=>el.classList.remove("active"));document.getElementById(id).classList.add("active");btn.classList.add("active")}

function ensureGlobalGanttTooltip(){
  let el=document.getElementById("global-gantt-tooltip");
  if(el)return el;
  el=document.createElement("div");
  el.id="global-gantt-tooltip";
  el.className="global-gantt-tooltip";
  document.body.appendChild(el);
  return el;
}

function ganttTooltipHtml(seg){
  const ds=seg.dataset||{};
  return `
    <div class="tooltip-title">${ds.tipProject||""}</div>
    <div class="tooltip-grid">
      <div class="tooltip-item"><span>Daily FTEs</span><strong>${ds.tipDailyfte||"0"}</strong></div>
      <div class="tooltip-item"><span>Total Days</span><strong>${ds.tipDays||"0"}</strong></div>
      <div class="tooltip-item"><span>Region</span><strong>${ds.tipRegion||"-"}</strong></div>
      <div class="tooltip-item"><span>Requestor</span><strong>${ds.tipRequestor||"-"}</strong></div>
      <div class="tooltip-item tooltip-item-wide"><span>Total Billing</span><strong>${ds.tipBilling||"$0.00"}</strong></div>
    </div>`;
}

function positionGlobalGanttTooltip(tip,event){
  const pad=12;
  const rect=tip.getBoundingClientRect();
  let left=event.clientX+16;
  let top=event.clientY-12;
  if(left+rect.width>window.innerWidth-pad){left=event.clientX-rect.width-16}
  if(left<pad){left=pad}
  if(top+rect.height>window.innerHeight-pad){top=window.innerHeight-rect.height-pad}
  if(top<pad){top=pad}
  tip.style.left=`${left}px`;
  tip.style.top=`${top}px`;
}

function bindGanttTooltipHandlers(){
  const tip=ensureGlobalGanttTooltip();
  let activeSeg=null;

  const show=(seg,event)=>{
    activeSeg=seg;
    tip.innerHTML=ganttTooltipHtml(seg);
    tip.classList.add("open");
    positionGlobalGanttTooltip(tip,event);
  };

  const hide=()=>{
    activeSeg=null;
    tip.classList.remove("open");
  };

  document.querySelectorAll(".gantt-segment-tooltip").forEach(seg=>{
    seg.addEventListener("mouseenter",e=>show(seg,e));
    seg.addEventListener("mousemove",e=>{if(activeSeg===seg)positionGlobalGanttTooltip(tip,e)});
    seg.addEventListener("mouseleave",hide);
  });
}

/* Insync Report Functions */
function getCurrentMonthString(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`}

function initializeInsyncReportModal(){
  const monthInput=document.getElementById("insync-month-selector");
  if(monthInput){monthInput.value=getCurrentMonthString()}
  loadInsyncReports()
}

async function generateInsyncReport(){
  const monthInput=document.getElementById("insync-month-selector");
  const month=monthInput?monthInput.value:"";
  if(!month){alert("Please select a month");return}
  try{
    const res=await fetch(`/api/reports/insync/generate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({month})});
    const data=await res.json();
    if(data.ok){alert("Report generated successfully");loadInsyncReports()}
    else{alert(data.message||"Error generating report")}
  }catch(err){console.error(err);alert("Error generating report")}
}

async function loadInsyncReports(){
  try{
    const res=await fetch(`/api/reports/insync/list`);
    const data=await res.json();
    renderInsyncReportsList(data.reports||[])
  }catch(err){console.error(err)}
}

function renderInsyncReportsList(reports){
  const listContainer=document.getElementById("insync-reports-list");
  if(!listContainer)return;
  if(reports.length===0){listContainer.innerHTML='<p class="muted">No reports generated yet. Select a month and click "Generate Report" to create one.</p>';return}
  listContainer.innerHTML=reports.map(r=>`
    <div class="report-item">
      <div class="report-item-info">
        <div class="report-item-month">${formatMonthDisplay(r.month)}</div>
        <div class="report-item-date">Generated: ${formatDate(r.generated_on)}</div>
      </div>
      <div class="report-item-actions">
        <a href="/api/reports/insync/download/${r.id}" class="report-download-link">Download</a>
      </div>
    </div>
  `).join("")
}

function formatMonthDisplay(month){
  if(!month||month.length!==7)return month;
  const[year,monthNum]=month.split("-");
  const monthNames=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${monthNames[parseInt(monthNum)-1]} ${year}`
}

function formatDate(dateStr){
  try{const d=new Date(dateStr);return d.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return dateStr}
}

/* Chat Functions */
async function sendChatMessage(){
  const input=document.getElementById("chat-input");
  const messagesContainer=document.getElementById("chat-messages");
  const loadingIndicator=document.getElementById("chat-loading");
  
  if(!input||!messagesContainer)return;
  
  const message=input.value.trim();
  if(!message)return;
  
  // Add user message to chat
  const userMsgDiv=document.createElement("div");
  userMsgDiv.className="chat-message user-message";
  userMsgDiv.style.cssText="margin-bottom: 16px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; text-align: right;";
  userMsgDiv.innerHTML=`
    <div style="font-weight: 600; margin-bottom: 4px; color: #fff;">You</div>
    <div>${escapeHtml(message)}</div>
  `;
  messagesContainer.appendChild(userMsgDiv);
  
  // Clear input and scroll
  input.value="";
  messagesContainer.scrollTop=messagesContainer.scrollHeight;
  
  // Create progress container
  const progressDiv=document.createElement("div");
  progressDiv.className="chat-message assistant-message";
  progressDiv.style.cssText="margin-bottom: 16px; padding: 12px; background: rgba(100,150,255,0.1); border-radius: 8px;";
  progressDiv.innerHTML=`
    <div style="font-weight: 600; margin-bottom: 8px; color: #6495ff;">Assistant</div>
    <div id="progress-steps" style="font-size: 13px; opacity: 0.8;"></div>
  `;
  messagesContainer.appendChild(progressDiv);
  messagesContainer.scrollTop=messagesContainer.scrollHeight;
  
  try{
    const res=await fetch("/api/chat",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message})
    });
    
    const data=await res.json();
    
    if(data.error){
      progressDiv.remove();
      addChatMessage("Error: "+data.error,"error");
    }else{
      // Animate progress steps
      const progressSteps=data.progress||[];
      const progressContainer=document.getElementById("progress-steps");
      
      if(progressContainer&&progressSteps.length>0){
        for(let i=0;i<progressSteps.length-1;i++){
          const step=progressSteps[i];
          const stepDiv=document.createElement("div");
          stepDiv.style.cssText="margin: 4px 0; opacity: 0; transition: opacity 0.3s;";
          stepDiv.innerHTML=`<span style="color: #6495ff;">✓</span> ${escapeHtml(step.status)}`;
          progressContainer.appendChild(stepDiv);
          
          // Fade in with delay
          await new Promise(resolve=>setTimeout(resolve,300));
          stepDiv.style.opacity="1";
          messagesContainer.scrollTop=messagesContainer.scrollHeight;
        }
        
        // Wait a moment then remove progress and show final answer
        await new Promise(resolve=>setTimeout(resolve,400));
      }
      
      progressDiv.remove();
      addChatMessage(data.message,"assistant");
    }
  }catch(err){
    console.error("Chat error:",err);
    progressDiv.remove();
    addChatMessage("Error: Unable to connect to chat service. Please try again.","error");
  }
}

function addChatMessage(content,type="assistant"){
  const messagesContainer=document.getElementById("chat-messages");
  if(!messagesContainer)return;
  
  const msgDiv=document.createElement("div");
  msgDiv.className=`chat-message ${type}-message`;
  
  if(type==="assistant"){
    msgDiv.style.cssText="margin-bottom: 16px; padding: 12px; background: rgba(100,150,255,0.1); border-radius: 8px;";
    msgDiv.innerHTML=`
      <div style="font-weight: 600; margin-bottom: 4px; color: #6495ff;">Assistant</div>
      <div style="white-space: pre-wrap;">${formatMarkdown(content)}</div>
    `;
  }else if(type==="error"){
    msgDiv.style.cssText="margin-bottom: 16px; padding: 12px; background: rgba(255,100,100,0.1); border-radius: 8px; color: #ff6464;";
    msgDiv.innerHTML=`
      <div style="font-weight: 600; margin-bottom: 4px;">Error</div>
      <div>${escapeHtml(content)}</div>
    `;
  }
  
  messagesContainer.appendChild(msgDiv);
  messagesContainer.scrollTop=messagesContainer.scrollHeight;
}

function escapeHtml(text){
  const div=document.createElement("div");
  div.textContent=text;
  return div.innerHTML;
}

function formatMarkdown(text){
  // Basic markdown formatting
  let formatted=escapeHtml(text);
  
  // Convert markdown tables to HTML tables
  const tableRegex=/(\|[^\n]+\|\n)(\|[-:\s|]+\|\n)((?:\|[^\n]+\|\n?)+)/g;
  formatted=formatted.replace(tableRegex,(match,header,separator,body)=>{
    const headerCells=header.split("|").filter(c=>c.trim()).map(c=>`<th>${c.trim()}</th>`).join("");
    const bodyRows=body.trim().split("\n").map(row=>{
      const cells=row.split("|").filter(c=>c.trim()).map(c=>`<td>${c.trim()}</td>`).join("");
      return `<tr>${cells}</tr>`;
    }).join("");
    return `<table class="data-table compact" style="margin: 12px 0; background: rgba(0,0,0,0.2);"><thead><tr>${headerCells}</tr></thead><tbody>${bodyRows}</tbody></table>`;
  });
  
  // Bold **text**
  formatted=formatted.replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>");
  
  // Italic *text*
  formatted=formatted.replace(/\*([^*]+)\*/g,"<em>$1</em>");
  
  // Code blocks
  formatted=formatted.replace(/```([^`]+)```/g,'<pre style="background: rgba(0,0,0,0.3); padding: 8px; border-radius: 4px; overflow-x: auto;"><code>$1</code></pre>');
  
  // Inline code
  formatted=formatted.replace(/`([^`]+)`/g,'<code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">$1</code>');
  
  return formatted;
}

document.addEventListener("DOMContentLoaded",()=>{
  const staffingDate=document.getElementById("staffing-date");
  if(staffingDate){
    staffingDate.value=todayString();
    staffingDate.addEventListener("change",()=>loadStaffingPrefill());
  }
  bindGanttTooltipHandlers();
  initializeInsyncReportModal()
})
