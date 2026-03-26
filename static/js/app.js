function openModal(id){const el=document.getElementById(id);if(el)el.classList.add("open")}
function closeModal(id){const el=document.getElementById(id);if(el)el.classList.remove("open")}
function toggleDropdown(id){document.querySelectorAll(".dropdown-card.open").forEach(el=>{if(el.id!==id)el.classList.remove("open")});const el=document.getElementById(id);if(el)el.classList.toggle("open")}
function closeDropdown(id){const el=document.getElementById(id);if(el)el.classList.remove("open")}
document.addEventListener("click",(e)=>{if(!e.target.closest(".dropdown-shell")&&!e.target.closest(".topbar-user-menu")){document.querySelectorAll(".dropdown-card.open").forEach(el=>el.classList.remove("open"))}})
function todayString(){return new Date().toISOString().slice(0,10)}
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
  projectInput.addEventListener("change",()=>{const meta=getProjectMetaByName(projectInput.value);if(meta){tr.querySelector(".case-code-input").value=meta.billing_case_code||"";tr.dataset.projectId=meta.id||""}else{tr.dataset.projectId=""}deriveBilling()});
  tr.querySelectorAll("input,select").forEach(inp=>{inp.addEventListener("change",deriveBilling);inp.addEventListener("keyup",deriveBilling)});
  const meta=getProjectMetaByName(data.project_name||"");tr.dataset.projectId=data.project_id||(meta?meta.id:"");return tr
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
    rows.push({employee_id:getEmployeeIdByName(employeeName),employee_name:employeeName,staffing_type:staffingType,project_id:projectMeta?projectMeta.id:(tr.dataset.projectId||""),project_name:projectName,case_code:caseCode,hours:hours,comments:comments})
  });return rows.filter(r=>r.employee_name||r.project_name||r.staffing_type||r.case_code)
}
function renderBillingRows(rows){const tbody=document.getElementById("billing-table-body");if(!tbody)return;tbody.innerHTML="";rows.forEach((row)=>{const tr=document.createElement("tr");tr.innerHTML=`<td>${row.project_name||""}</td><td>${row.project_type||""}</td><td>${row.case_code||""}</td><td><input class="glass-input table-input" type="number" step="0.01" value="${row.billable_ftes||0}" /></td><td><input class="glass-input table-input" type="number" step="0.01" value="${row.billing_amount||0}" /></td><td><input class="glass-input table-input" value="${row.comments||""}" /></td>`;tr.dataset.projectId=row.project_id||"";tr.dataset.projectName=row.project_name||"";tr.dataset.projectType=row.project_type||"";tr.dataset.caseCode=row.case_code||"";tbody.appendChild(tr)})}
function billingRowsPayload(){const rows=[];document.querySelectorAll("#billing-table-body tr").forEach(tr=>{const inputs=tr.querySelectorAll("input");rows.push({project_id:tr.dataset.projectId||"",project_name:tr.dataset.projectName||"",project_type:tr.dataset.projectType||"",case_code:tr.dataset.caseCode||"",billable_ftes:parseFloat(inputs[0].value||"0"),billing_amount:parseFloat(inputs[1].value||"0"),comments:inputs[2].value.trim()})});return rows}
async function deriveBilling(){const rows=staffingRowsPayload();const res=await fetch("/api/staffing/derive-billing",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({rows})});const data=await res.json();renderBillingRows(data.billing_rows||[])}
function addStaffingRow(data={}){const tbody=document.getElementById("staffing-table-body");if(tbody)tbody.appendChild(createStaffingRow(data))}
function clearStaffingRows(){const tbody=document.getElementById("staffing-table-body");const billing=document.getElementById("billing-table-body");if(tbody)tbody.innerHTML="";if(billing)billing.innerHTML=""}
async function loadStaffingPrefill(customDate=""){const dateInput=document.getElementById("staffing-date");if(dateInput&&!dateInput.value)dateInput.value=todayString();const date=dateInput?dateInput.value:todayString();let url=`/api/staffing/prefill?date=${encodeURIComponent(date)}`;if(customDate)url+=`&load_date=${encodeURIComponent(customDate)}`;const res=await fetch(url);const data=await res.json();const label=document.getElementById("prefill-date-label");if(label)label.textContent=data.source_date||"—";clearStaffingRows();const rows=data.rows||[];if(rows.length===0){addStaffingRow();renderBillingRows([]);return}rows.forEach(r=>addStaffingRow(r));renderBillingRows(data.billing_rows||[])}
function loadFromCustomDate(){const input=document.getElementById("load-date");if(input&&input.value){loadStaffingPrefill(input.value);closeModal("load-modal")}}
async function saveStaffingRows(){const date=document.getElementById("staffing-date").value||todayString();const rows=staffingRowsPayload();const billingRows=billingRowsPayload();const res=await fetch("/api/staffing/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({date,rows,billing_rows:billingRows})});const data=await res.json();alert(data.message||"Saved");closeModal("staffing-modal")}
async function submitProjectForm(event){event.preventDefault();const formData=new FormData(event.target);const res=await fetch("/api/projects/create",{method:"POST",body:formData});const data=await res.json();if(data.ok){alert("Project added. Refresh the page to see it in the current projects list.");event.target.reset()}else{alert(data.message||"Unable to add project")}}
function showReportTab(id,btn){document.querySelectorAll(".report-tab").forEach(el=>el.classList.remove("active"));document.querySelectorAll(".tab").forEach(el=>el.classList.remove("active"));document.getElementById(id).classList.add("active");btn.classList.add("active")}

/* Insync Report Functions */
function getCurrentMonthString(){const d=new Date();return d.toISOString().slice(0,7)}

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

document.addEventListener("DOMContentLoaded",()=>{
  const staffingDate=document.getElementById("staffing-date");
  if(staffingDate)staffingDate.value=todayString();
  initializeInsyncReportModal()
})
