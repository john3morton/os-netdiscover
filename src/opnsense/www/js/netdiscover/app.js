/* global mapDataToFormUI, saveFormToEndpoint, ajaxCall */

(function () {
  $(function () {
  const intFields = [
    'general.interval',
    'general.max_hosts',
    'general.rate_limit_ms',
    'general.ssdp_xml_rate_limit',
    'general.tcp_probe_timeout_ms',
    'general.snmp_timeout_ms',
    'general.snmp_rate_limit'
  ];

  function toInt(payload) {
    if (/^[+-]?[0-9]+$/.test(payload)) {
      return parseInt(payload, 10);
    }
    return payload;
  }
  window.toInt = toInt;

  intFields.forEach(function (id) {
    const el = document.getElementById(id);
    if (el) el.setAttribute('type_formatter', 'toInt');
  });

  const defaults = {
    enabled: '0',
    interval: '300',
    active_scan: '0',
    reverse_dns: '1',
    interfaces: '_LAN_',
    max_hosts: '4096',
    rate_limit_ms: '3',
    ssdp_enable: '1',
    ssdp_fetch_xml: '1',
    ssdp_xml_rate_limit: '10',
    mdns_enable: '1',
    llmnr_enable: '1',
    nbns_enable: '1',
    tcp_probe_enable: '0',
    tcp_probe_ports: '22,80,443,445,3389,9100',
    tcp_probe_timeout_ms: '250',
    snmp_enable: '0',
    snmp_communities: 'public',
    snmp_timeout_ms: '400',
    snmp_rate_limit: '3600'
  };

  const boolFieldKeys = [
    'enabled',
    'active_scan',
    'reverse_dns',
    'ssdp_enable',
    'ssdp_fetch_xml',
    'mdns_enable',
    'llmnr_enable',
    'nbns_enable',
    'tcp_probe_enable',
    'snmp_enable'
  ];

  // Port to service name mapping (v2.0.8)
  const portServices = {
    20: 'FTP-Data', 21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP',
    53: 'DNS', 67: 'DHCP-Server', 68: 'DHCP-Client', 69: 'TFTP',
    80: 'HTTP', 110: 'POP3', 123: 'NTP', 135: 'MS-RPC', 137: 'NetBIOS-NS',
    138: 'NetBIOS-DGM', 139: 'NetBIOS-SSN', 143: 'IMAP', 161: 'SNMP',
    162: 'SNMP-Trap', 389: 'LDAP', 443: 'HTTPS', 445: 'SMB', 465: 'SMTPS',
    514: 'Syslog', 515: 'LPD', 587: 'SMTP-Submit', 631: 'IPP', 636: 'LDAPS',
    873: 'Rsync', 902: 'VMware', 993: 'IMAPS', 995: 'POP3S',
    1433: 'MS-SQL', 1521: 'Oracle', 1723: 'PPTP', 2049: 'NFS',
    3306: 'MySQL', 3389: 'RDP', 5000: 'UPnP', 5060: 'SIP', 5432: 'PostgreSQL',
    5900: 'VNC', 6379: 'Redis', 8080: 'HTTP-Alt', 8443: 'HTTPS-Alt',
    8888: 'HTTP-Alt2', 9100: 'Printer', 27017: 'MongoDB'
  };
  
  function formatPort(port) {
    const portNum = parseInt(port);
    const service = portServices[portNum];
    return service ? portNum + '/' + service : portNum;
  }
  
  function formatPorts(ports) {
    if (!Array.isArray(ports) || ports.length === 0) return '';
    return ports.map(p => formatPort(p)).join(', ');
  }
  
  // add styles for table features
  (function addStyle() {
    const id = 'nd-table-styles';
    if (document.getElementById(id)) return;
    const s = document.createElement('style');
    s.id = id;
    s.textContent = `
      .nd-nondefault{box-shadow:0 0 0 2px #f0ad4e inset;}
      .nd-sortable-col{cursor:pointer;user-select:none;position:relative;}
      .nd-sortable-col:hover{background-color:rgba(255,255,255,0.05);}
      .nd-th-content{display:inline-flex;align-items:center;gap:6px;width:100%;}
      .nd-th-content i{flex-shrink:0;font-size:11px;opacity:0.7;}
      .nd-resizable-col{position:relative;}
      .nd-resize-handle{position:absolute;top:0;right:0;width:5px;height:100%;cursor:col-resize;background:transparent;}
      .nd-resize-handle:hover{background:rgba(255,255,255,0.2);}
      .nd-resizable{table-layout:fixed;width:100%;}
      .nd-resizable th, .nd-resizable td{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
      #gridEvents tbody tr[style*="cursor: pointer"]:hover{background-color:rgba(255,255,255,0.08) !important;}
    `;
    document.head.appendChild(s);
  })();

  function toggleDiff(el, isDiff) {
    if (isDiff) {
      el.classList.add('nd-nondefault');
    } else {
      el.classList.remove('nd-nondefault');
    }
  }

  function applyFieldValue(key, val) {
    const fullId = 'general.' + key;
    const el = document.getElementById(fullId);
    if (!el) {
      console.log('Field not found: ' + fullId);
      return;
    }
    const def = defaults[key];
    
    // Set tooltip to show default
    if (def !== undefined) {
      el.setAttribute('title', 'Default: ' + def);
    }
    
    const isBool = boolFieldKeys.indexOf(key) !== -1;
    
    if (isBool) {
      // For checkboxes: use saved value if present, otherwise use default
      const useVal = (val === '' || val === null || val === undefined) ? def : val;
      const checked = (useVal === '1' || useVal === 1 || useVal === true);
      console.log('Setting checkbox ' + key + ' to ' + checked + ' (val=' + val + ', useVal=' + useVal + ')');
      $(el).prop('checked', checked);
      const defChecked = (def === '1' || def === 1 || def === true);
      toggleDiff(el, checked !== defChecked);
    } else {
      // For text fields: use saved value if present, otherwise use default
      const useVal = (val === '' || val === null || val === undefined) ? def : val;
      const v = (useVal !== undefined && useVal !== null) ? String(useVal) : '';
      el.value = v;
      toggleDiff(el, v !== String(def));
    }
  }

  function loadSettings() {
    $.ajax({
      url: '/api/netdiscover/settings/get',
      type: 'GET',
      cache: false,
      dataType: 'json',
      success: function (data) {
        console.log('Settings loaded:', data);
        const g = (data && data.netdiscover && data.netdiscover.general) ? data.netdiscover.general : {};
      
      // Wait a tick for mapDataToFormUI to populate DOM
      setTimeout(function() {
        // Debug: find actual field IDs
        const allInputs = document.querySelectorAll('input[id*="general"], select[id*="general"]');
        console.log('Found ' + allInputs.length + ' general fields');
        if (allInputs.length > 0) {
          console.log('First 3 field IDs:', Array.from(allInputs).slice(0,3).map(e => e.id));
        }
        
        // Apply all fields
        Object.keys(defaults).forEach(function (k) {
          const apiVal = g[k];
          applyFieldValue(k, apiVal);
        });
        
        baseline = snapshotCurrent();
        hideSave();
        hideApply();
        wireDirtyHandlers();
      }, 100);
      }
    });
  }

  loadSettings();

  function showSaveMsg() {
    const m = document.getElementById('saveMsg');
    m.style.display = 'block';
  }

  const btnSave = document.getElementById('btn_save');
  const btnApply = document.getElementById('btn_apply');
  function hideSave() { if (btnSave) btnSave.style.display = 'none'; }
  function showSave() { if (btnSave) btnSave.style.display = 'inline-block'; }
  function hideApply() { if (btnApply) btnApply.style.display = 'none'; }
  function showApply() { if (btnApply) btnApply.style.display = 'inline-block'; }

  let baseline = {};
  let fieldKeys = Object.keys(defaults);

  function snapshotCurrent() {
    const out = {};
    fieldKeys.forEach(function (k) {
      const el = document.getElementById('general.' + k);
      if (!el) return;
      if (el.type === 'checkbox') {
        out[k] = el.checked ? '1' : '0';
      } else {
        out[k] = (el.value !== undefined && el.value !== null) ? String(el.value) : '';
      }
    });
    return out;
  }

  function isDirty() {
    const cur = snapshotCurrent();
    return fieldKeys.some(function (k) {
      const b = (baseline[k] !== undefined) ? String(baseline[k]) : '';
      const c = (cur[k] !== undefined) ? String(cur[k]) : '';
      return b !== c;
    });
  }

  function wireDirtyHandlers() {
    fieldKeys.forEach(function (k) {
      const el = document.getElementById('general.' + k);
      if (!el) return;
      el.addEventListener('change', updateButtons);
      el.addEventListener('input', updateButtons);
    });
  }

  function updateButtons() {
    if (isDirty()) {
      showSave();
      hideApply();
    } else {
      hideSave();
      hideApply();
    }
  }

  if (btnSave) {
    btnSave.addEventListener('click', function () {
      // Build payload from actual field values
      const payload = {netdiscover: {general: {}}};
      Object.keys(defaults).forEach(function(k) {
        const el = document.getElementById('general.' + k);
        if (!el) return;
        if (el.type === 'checkbox') {
          payload.netdiscover.general[k] = el.checked ? '1' : '0';
        } else {
          payload.netdiscover.general[k] = el.value || '';
        }
      });
      console.log('Payload being saved:', JSON.stringify(payload));
      
      $.ajax({
        url: '/api/netdiscover/settings/set',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(payload),
        success: function(data) {
          console.log('Save response (full):', data);
          if (data && data.validations) {
            console.warn('Validation errors:', data.validations);
          }
          if (data && data.result === 'failed') {
            console.error('Save reported failed:', data);
          }
          // Reload to verify
          setTimeout(function() {
            $.ajax({
              url: '/api/netdiscover/settings/get',
              type: 'GET',
              success: function(check) {
                console.log('Post-save verification:', check);
              }
            });
          }, 500);
          showSaveMsg();
          baseline = snapshotCurrent();
          hideSave();
          showApply();
        },
        error: function(xhr, status, error) {
          console.error('Save failed:', status, error);
        }
      });
    });
  }

  if (btnApply) {
    btnApply.addEventListener('click', function () {
      ajaxCall('/api/netdiscover/service/reconfigure', {}, function () {
        const m = document.getElementById('saveMsg');
        if (m) m.style.display = 'none';
        hideApply();
        baseline = snapshotCurrent();
      });
    });
  }
  
  // Update OUI database buttons (IEEE and Wireshark)
  function updateOuiDatabase(source) {
    const statusEl = document.getElementById('oui_update_status');
    const btnIeee = document.getElementById('btn_update_oui_ieee');
    const btnWireshark = document.getElementById('btn_update_oui_wireshark');
    
    if (btnIeee) btnIeee.disabled = true;
    if (btnWireshark) btnWireshark.disabled = true;
    
    const sourceName = source === 'ieee' ? 'IEEE OUI' : 'Wireshark Extended';
    statusEl.innerHTML = '<div class="alert alert-info"><i class="fa fa-spinner fa-spin"></i> Downloading ' + sourceName + ' database and backfilling device vendors... (30-60 seconds)</div>';
    
    const url = source === 'ieee' ? '/api/netdiscover/service/updateoui' : '/api/netdiscover/service/updatewireshark';
    
    $.ajax({
      url: url,
      type: 'GET',
      timeout: 90000,
      success: function(data) {
        if (data.status === 'success') {
          let msg = sourceName + ' database updated! ' + (data.entries || 0) + ' vendor entries loaded.';
          if (data.output && data.output.indexOf('Updated') > -1) {
            const match = data.output.match(/Updated (\d+) device/);
            if (match) {
              msg += ' Backfilled ' + match[1] + ' device(s).';
            }
          }
          statusEl.innerHTML = '<div class="alert alert-success"><i class="fa fa-check"></i> ' + msg + '</div>';
          
          if (typeof loadInventoryData === 'function') {
            setTimeout(loadInventoryData, 1000);
          }
          
          setTimeout(function() {
            statusEl.innerHTML = '';
          }, 8000);
        } else {
          statusEl.innerHTML = '<div class="alert alert-danger"><i class="fa fa-exclamation-triangle"></i> Update failed: ' + (data.message || 'Unknown error') + '</div>';
        }
      },
      error: function(xhr) {
        statusEl.innerHTML = '<div class="alert alert-danger"><i class="fa fa-exclamation-triangle"></i> Update failed: ' + (xhr.statusText || 'Network error') + '</div>';
      },
      complete: function() {
        if (btnIeee) btnIeee.disabled = false;
        if (btnWireshark) btnWireshark.disabled = false;
      }
    });
  }
  
  const btnUpdateOuiIeee = document.getElementById('btn_update_oui_ieee');
  if (btnUpdateOuiIeee) {
    btnUpdateOuiIeee.addEventListener('click', function() {
      updateOuiDatabase('ieee');
    });
  }
  
  const btnUpdateOuiWireshark = document.getElementById('btn_update_oui_wireshark');
  if (btnUpdateOuiWireshark) {
    btnUpdateOuiWireshark.addEventListener('click', function() {
      updateOuiDatabase('wireshark');
    });
  }

  function epochFormatter(column, row) {
    const v = row[column.id];
    if (!v) return '';
    const d = new Date(parseInt(v, 10) * 1000);
    return d.toLocaleString();
  }

  function listFormatter(column, row) {
    const v = row[column.id];
    if (!v) return '';
    if (Array.isArray(v)) return v.join(',');
    return '' + v;
  }

  function jsonFormatter(column, row) {
    const v = row[column.id];
    if (!v) return '';
    try {
      return JSON.stringify(v);
    } catch (e) {
      return '' + v;
    }
  }

  // State management with localStorage persistence (v1.5.0 - dual filters, v2.0.9 - category filter)
  let ndFlagFilter = localStorage.getItem('nd_flag_filter') || '';  // new/changed/back
  let ndConnFilter = localStorage.getItem('nd_conn_filter') || '';  // online/offline/missing/gone
  let ndCategoryFilter = localStorage.getItem('nd_category_filter') || '';  // Network/Computer/Mobile/etc
  let invSearchTerm = localStorage.getItem('nd_inv_search') || '';
  let invSortColumn = localStorage.getItem('nd_inv_sort_col') || 'ip';
  let invSortDir = localStorage.getItem('nd_inv_sort_dir') || 'asc';
  let invData = [];
  let selectedDevices = new Set();
  
  // Column visibility defaults (v2.0.0 - added via_ap column)
  const defaultColumns = {
    mac: true, hostname: true, vendor: true,
    device_type: true, tags: true, model: true, os: true,
    mdns_services: true, open_ports: true, snmp_sysname: false,
    snmp_sysdescr: false, interface: true, subnet: true, via_ap: true
  };
  // Note: flags, connection, DHCP columns always visible (not configurable)
  
  let visibleColumns = {};
  try {
    const saved = localStorage.getItem('nd_visible_columns');
    visibleColumns = saved ? JSON.parse(saved) : {...defaultColumns};
  } catch(e) {
    visibleColumns = {...defaultColumns};
  }
  
  function updateFilterState() {
    // Update lifecycle flag buttons
    document.querySelectorAll('.nd-filter-flag').forEach((b)=>{
      const btnFlag = b.getAttribute('data-flag') || '';
      if (btnFlag === ndFlagFilter) {
        b.classList.add('btn-primary');
        b.classList.remove('btn-default');
      } else {
        b.classList.remove('btn-primary');
        b.classList.add('btn-default');
      }
    });
    
    // Update connection state buttons
    document.querySelectorAll('.nd-filter-conn').forEach((b)=>{
      const btnConn = b.getAttribute('data-conn') || '';
      if (btnConn === ndConnFilter) {
        b.classList.add('btn-primary');
        b.classList.remove('btn-default');
      } else {
        b.classList.remove('btn-primary');
        b.classList.add('btn-default');
      }
    });
    
    // Update category filter buttons (v2.0.9)
    document.querySelectorAll('.nd-filter-category').forEach((b)=>{
      const btnCategory = b.getAttribute('data-category') || '';
      if (btnCategory === ndCategoryFilter) {
        b.classList.add('btn-primary');
        b.classList.remove('btn-default');
      } else {
        b.classList.remove('btn-primary');
        b.classList.add('btn-default');
      }
    });
  }
  
  // Restore filter state on page load
  updateFilterState();

  // Lifecycle flag filter buttons
  document.querySelectorAll('.nd-filter-flag').forEach((btn)=>{
    btn.addEventListener('click', ()=>{
      ndFlagFilter = btn.getAttribute('data-flag') || '';
      localStorage.setItem('nd_flag_filter', ndFlagFilter);
      updateFilterState();
      renderInventoryTable();
    });
  });
  
  // Connection state filter buttons
  document.querySelectorAll('.nd-filter-conn').forEach((btn)=>{
    btn.addEventListener('click', ()=>{
      ndConnFilter = btn.getAttribute('data-conn') || '';
      localStorage.setItem('nd_conn_filter', ndConnFilter);
      updateFilterState();
      renderInventoryTable();
    });
  });
  
  // Category filter buttons (v2.0.9)
  document.querySelectorAll('.nd-filter-category').forEach((btn)=>{
    btn.addEventListener('click', ()=>{
      ndCategoryFilter = btn.getAttribute('data-category') || '';
      localStorage.setItem('nd_category_filter', ndCategoryFilter);
      updateFilterState();
      renderInventoryTable();
    });
  });
  
  // Search box functionality
  const invSearchInput = document.getElementById('inv_search');
  if (invSearchInput) {
    // Restore saved search term
    invSearchInput.value = invSearchTerm;
    
    invSearchInput.addEventListener('input', function() {
      invSearchTerm = this.value.toLowerCase();
      localStorage.setItem('nd_inv_search', invSearchTerm);
      renderInventoryTable();
    });
  }
  
  const invSearchClear = document.getElementById('inv_search_clear');
  if (invSearchClear) {
    invSearchClear.addEventListener('click', function() {
      if (invSearchInput) {
        invSearchInput.value = '';
        invSearchTerm = '';
        localStorage.removeItem('nd_inv_search');
        renderInventoryTable();
      }
    });
  }
  
  // Column sorting
  document.querySelectorAll('#gridDevices .nd-sortable-col').forEach((th)=>{
    th.addEventListener('click', function(e) {
      // Don't sort if clicking on resize handle
      if (e.target.classList.contains('nd-resize-handle')) return;
      
      const col = this.getAttribute('data-column-id');
      if (invSortColumn === col) {
        invSortDir = (invSortDir === 'asc') ? 'desc' : 'asc';
      } else {
        invSortColumn = col;
        invSortDir = 'asc';
      }
      
      // Save to localStorage
      localStorage.setItem('nd_inv_sort_col', invSortColumn);
      localStorage.setItem('nd_inv_sort_dir', invSortDir);
      
      // Update sort icons
      document.querySelectorAll('#gridDevices .nd-sortable-col i').forEach((icon)=>{
        icon.className = 'fa fa-sort';
      });
      const icon = this.querySelector('i');
      if (icon) {
        icon.className = invSortDir === 'asc' ? 'fa fa-sort-asc' : 'fa fa-sort-desc';
      }
      
      renderInventoryTable();
    });
  });
  
  // Column resizing
  let resizingColumn = null;
  let startX = 0;
  let startWidth = 0;
  
  document.querySelectorAll('#gridDevices .nd-resize-handle').forEach((handle)=>{
    handle.addEventListener('mousedown', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      resizingColumn = this.parentElement;
      startX = e.pageX;
      startWidth = resizingColumn.offsetWidth;
      
      document.addEventListener('mousemove', onColumnResize);
      document.addEventListener('mouseup', stopColumnResize);
    });
  });
  
  function onColumnResize(e) {
    if (!resizingColumn) return;
    const diff = e.pageX - startX;
    const newWidth = Math.max(50, startWidth + diff);
    resizingColumn.style.width = newWidth + 'px';
  }
  
  function stopColumnResize() {
    if (resizingColumn) {
      // Save column width to localStorage
      const colId = resizingColumn.getAttribute('data-column-id');
      const width = resizingColumn.offsetWidth;
      localStorage.setItem('nd_col_width_' + colId, width);
    }
    
    resizingColumn = null;
    document.removeEventListener('mousemove', onColumnResize);
    document.removeEventListener('mouseup', stopColumnResize);
  }
  
  // Restore saved column widths
  document.querySelectorAll('#gridDevices .nd-resizable-col').forEach((th)=>{
    const colId = th.getAttribute('data-column-id');
    const savedWidth = localStorage.getItem('nd_col_width_' + colId);
    if (savedWidth) {
      th.style.width = savedWidth + 'px';
    }
  });

  const exp = document.getElementById('btn_export_csv');
  if (exp) {
    exp.addEventListener('click', ()=>{
      const url = '/api/netdiscover/export/inventory?status=' + encodeURIComponent(ndStatusFilter) + '&search=' + encodeURIComponent(invSearchTerm || '');
      window.open(url, '_blank');
    });
  }
  
  // Select All checkbox
  const selectAllCb = document.getElementById('select_all_devices');
  if (selectAllCb) {
    selectAllCb.addEventListener('change', function() {
      const checked = this.checked;
      document.querySelectorAll('.device-select-cb').forEach((cb)=>{
        cb.checked = checked;
        const ip = $(cb).data('ip');
        if (checked) {
          selectedDevices.add(ip);
        } else {
          selectedDevices.delete(ip);
        }
      });
      updateBulkActions();
    });
  }
  
  function updateBulkActions() {
    const count = selectedDevices.size;
    const bulkActions = document.getElementById('bulk_actions');
    const countEl = document.getElementById('nd_selected_count');
    
    if (count > 0) {
      bulkActions.style.display = 'block';
      countEl.style.display = 'inline-block';
      countEl.textContent = count + ' selected';
    } else {
      bulkActions.style.display = 'none';
      countEl.style.display = 'none';
    }
    
    // Update select all checkbox state
    const totalVisible = document.querySelectorAll('.device-select-cb').length;
    if (selectAllCb) {
      selectAllCb.checked = (count > 0 && count === totalVisible);
      selectAllCb.indeterminate = (count > 0 && count < totalVisible);
    }
  }

  // Initialize grids only when tabs are shown
  let inventoryGridInitialized = false;
  let eventsGridInitialized = false;
  let inventoryRefreshInterval = null;
  let eventsRefreshInterval = null;
  const REFRESH_INTERVAL_MS = 30000; // 30 seconds

  console.log('Setting up tab handlers...');

  function loadInventoryData() {
    const refreshBtn = document.getElementById('btn_refresh_inv');
    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.querySelector('i').classList.add('fa-spin');
    }
    
    $.ajax({
      url: '/api/netdiscover/inventory/search',
      type: 'POST',
      data: {current: 1, rowCount: 9999},
      success: function(response) {
        console.log('Inventory loaded:', response.rows.length, 'devices');
        invData = response.rows;
        renderInventoryTable();
        
        // Update last update timestamp
        const updateEl = document.getElementById('inv_last_update');
        if (updateEl) {
          updateEl.textContent = 'Updated: ' + new Date().toLocaleTimeString();
        }
      },
      error: function(xhr) {
        console.error('Inventory load failed:', xhr.status, xhr.responseText);
      },
      complete: function() {
        if (refreshBtn) {
          refreshBtn.disabled = false;
          refreshBtn.querySelector('i').classList.remove('fa-spin');
        }
      }
    });
  }
  
  // Manual refresh button
  const btnRefreshInv = document.getElementById('btn_refresh_inv');
  if (btnRefreshInv) {
    btnRefreshInv.addEventListener('click', function() {
      loadInventoryData();
    });
  }
  
  // Column configuration
  const btnColumnsInv = document.getElementById('btn_columns_inv');
  if (btnColumnsInv) {
    btnColumnsInv.addEventListener('click', function() {
      // Update checkboxes based on current state
      document.querySelectorAll('.col-toggle').forEach((cb)=>{
        const col = cb.getAttribute('data-col');
        cb.checked = visibleColumns[col] !== false;
      });
      $('#columnConfigModal').modal('show');
    });
  }
  
  // Status legend button
  const btnStatusLegend = document.getElementById('btn_status_legend');
  if (btnStatusLegend) {
    btnStatusLegend.addEventListener('click', function() {
      $('#statusLegendModal').modal('show');
    });
  }
  
  // Column toggle checkboxes
  $(document).on('change', '.col-toggle', function() {
    const col = this.getAttribute('data-col');
    visibleColumns[col] = this.checked;
    localStorage.setItem('nd_visible_columns', JSON.stringify(visibleColumns));
    applyColumnVisibility();
  });
  
  // Reset columns to defaults
  $(document).on('click', '#btn_reset_columns', function() {
    visibleColumns = {...defaultColumns};
    localStorage.setItem('nd_visible_columns', JSON.stringify(visibleColumns));
    document.querySelectorAll('.col-toggle').forEach((cb)=>{
      const col = cb.getAttribute('data-col');
      cb.checked = visibleColumns[col] !== false;
    });
    applyColumnVisibility();
  });
  
  function applyColumnVisibility() {
    // Show/hide columns in table
    Object.keys(visibleColumns).forEach((col)=>{
      const isVisible = visibleColumns[col];
      const selector = `[data-column-id="${col}"]`;
      document.querySelectorAll('#gridDevices ' + selector).forEach((el)=>{
        el.style.display = isVisible ? '' : 'none';
      });
    });
  }
  
  // Apply saved column visibility on load
  applyColumnVisibility();
  
  function renderInventoryTable() {
    let filtered = invData.slice();
    
    // Apply lifecycle flag filter (v1.5.0)
    if (ndFlagFilter) {
      filtered = filtered.filter(function(row) {
        const flags = (row.lifecycle_flags || '').toLowerCase();
        const filterFlag = ndFlagFilter.toLowerCase();
        // Check if filter flag is in comma-separated flags list
        return flags.includes(filterFlag);
      });
    }
    
    // Apply connection state filter (v1.5.0)
    if (ndConnFilter) {
      filtered = filtered.filter(function(row) {
        const connState = (row.connection_state || row.status || '').toLowerCase();
        const filterConn = ndConnFilter.toLowerCase();
        return connState === filterConn || connState.includes(filterConn);
      });
    }
    
    // Apply category filter (v2.0.9)
    if (ndCategoryFilter) {
      filtered = filtered.filter(function(row) {
        const category = (row.device_category || '').toLowerCase();
        const filterCategory = ndCategoryFilter.toLowerCase();
        return category === filterCategory;
      });
    }
    
    // Apply search filter
    if (invSearchTerm) {
      filtered = filtered.filter(function(row) {
        const searchable = [
          row.ip || '',
          row.mac || '',
          row.hostname || '',
          row.vendor || '',
          row.device_type || '',
          row.manufacturer || '',
          row.model || '',
          row.snmp_sysname || '',
          row.snmp_sysdescr || '',
          row.interface || '',
          row.subnet || '',
          (row.tags || []).join(' '),
          (row.mdns_services || []).join(' '),
          (row.open_ports || []).join(' ')
        ].join(' ').toLowerCase();
        return searchable.indexOf(invSearchTerm) !== -1;
      });
    }
    
    // Apply sorting
    filtered.sort(function(a, b) {
      let aVal = a[invSortColumn] || '';
      let bVal = b[invSortColumn] || '';
      
      // Special handling for IP addresses (numeric per octet)
      if (invSortColumn === 'ip') {
        aVal = ipToNumber(aVal);
        bVal = ipToNumber(bVal);
        const cmp = aVal - bVal;
        return invSortDir === 'asc' ? cmp : -cmp;
      }
      
      // Special handling for last_seen (numeric)
      if (invSortColumn === 'last_seen') {
        aVal = parseInt(aVal) || 0;
        bVal = parseInt(bVal) || 0;
        const cmp = aVal - bVal;
        return invSortDir === 'asc' ? cmp : -cmp;
      }
      
      // Array fields
      if (Array.isArray(aVal)) {
        aVal = aVal.join(',');
      }
      if (Array.isArray(bVal)) {
        bVal = bVal.join(',');
      }
      
      // String comparison
      aVal = String(aVal).toLowerCase();
      bVal = String(bVal).toLowerCase();
      
      if (aVal < bVal) return invSortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return invSortDir === 'asc' ? 1 : -1;
      return 0;
    });
    
    // Render rows
        const tbody = $('<tbody></tbody>');
    filtered.forEach(function(row) {
          const tr = $('<tr></tr>');
          tr.data('device', row);
          
      // Checkbox column
      const checkCell = $('<td></td>');
      const checkbox = $('<input type="checkbox" class="device-select-cb">');
      checkbox.data('ip', row.ip);
      checkbox.prop('checked', selectedDevices.has(row.ip));
      checkbox.on('change', function() {
        if (this.checked) {
          selectedDevices.add(row.ip);
        } else {
          selectedDevices.delete(row.ip);
        }
        updateBulkActions();
      });
      checkCell.append(checkbox);
      tr.append(checkCell);
      
      // View button column (left side)
      const viewCell = $('<td></td>');
      const viewBtn = $('<button class="btn btn-xs btn-info btn-view-device" title="View Details"><i class="fa fa-eye"></i></button>');
      viewBtn.on('click', function(e) {
        e.stopPropagation();
        openDetailModal(row);
      });
      viewCell.append(viewBtn);
      tr.append(viewCell);
      
      // Make row clickable to view details
      tr.css('cursor', 'pointer');
      tr.on('click', function(e) {
        if (!$(e.target).is('input, button, a')) {
          openDetailModal(row);
        }
      });
      
      // Lifecycle flags column (v1.5.0) - colored balls only
      const flagsCell = $('<td data-column-id="flags" style="text-align:center;"></td>');
      const flags = (row.lifecycle_flags || '').split(',').map(f => f.trim()).filter(f => f);
      
      if (flags.length > 0) {
        const flagContainer = $('<div style="display:inline-flex;gap:3px;"></div>');
        flags.forEach(function(flag) {
          let color = '#999';
          let title = flag;
          if (flag === 'new') {
            color = '#f0ad4e'; // orange
            title = 'New - First discovered';
          } else if (flag === 'changed') {
            color = '#428bca'; // light blue
            title = 'Changed - Attributes modified';
          } else if (flag === 'back') {
            color = '#5bc0de'; // cyan
            title = 'Back - Just returned online';
          }
          
          const dot = $('<span style="display:inline-block;width:12px;height:12px;border-radius:50%;"></span>')
            .css('background-color', color)
            .attr('title', title);
          flagContainer.append(dot);
        });
        flagsCell.append(flagContainer);
      }
      tr.append(flagsCell);
      
      // Connection state column (v1.5.0) - colored ball only
      const connCell = $('<td data-column-id="connection" style="text-align:center;"></td>');
      const connState = row.connection_state || 'online';
      
      let connColor = '#999';
      let connTitle = connState;
      if (connState === 'online') {
        connColor = '#5cb85c'; // green
        connTitle = 'Online - Currently reachable';
      } else if (connState === 'offline') {
        connColor = '#f0ad4e'; // yellow/orange
        connTitle = 'Offline - Not seen for 2+ scan cycles';
      } else if (connState === 'missing') {
        connColor = '#ff8c00'; // dark orange
        connTitle = 'Missing - Not seen for 30 days';
      } else if (connState === 'gone') {
        connColor = '#d9534f'; // red
        connTitle = 'Gone - Not seen for 60 days';
      }
      
      const connDot = $('<span style="display:inline-block;width:12px;height:12px;border-radius:50%;"></span>')
        .css('background-color', connColor)
        .attr('title', connTitle);
      connCell.append(connDot);
      tr.append(connCell);
      
      // Now IP and other columns in order
      tr.append($('<td data-column-id="ip"></td>').text(row.ip || ''));
      
      // DHCP type column (v1.5.1) - colored ball only
      const dhcpCell = $('<td data-column-id="dhcp" style="text-align:center;"></td>');
      const dhcpType = row.dhcp_type || 'unknown';
      
      let dhcpColor = '#999';
      let dhcpTitle = dhcpType;
      if (dhcpType === 'static') {
        dhcpColor = '#5bc0de'; // cyan/blue
        dhcpTitle = 'Static - Outside DHCP range';
      } else if (dhcpType === 'reserved') {
        dhcpColor = '#f0ad4e'; // orange/yellow
        dhcpTitle = 'Reserved - MAC-based DHCP reservation';
      } else if (dhcpType === 'dynamic') {
        dhcpColor = '#5cb85c'; // green
        dhcpTitle = 'Dynamic - DHCP lease';
      } else {
        dhcpColor = '#999'; // gray
        dhcpTitle = 'Unknown - Could not determine';
      }
      
      const dhcpDot = $('<span style="display:inline-block;width:10px;height:10px;border-radius:50%;"></span>')
        .css('background-color', dhcpColor)
        .attr('title', dhcpTitle);
      dhcpCell.append(dhcpDot);
      tr.append(dhcpCell);
      
      tr.append($('<td data-column-id="mac"></td>').text(row.mac || ''));
      
      const hostnameCell = $('<td data-column-id="hostname"></td>').text(row.hostname || '');
          if (row.hostname_override) {
            hostnameCell.append(' <span class="label label-info" title="Custom hostname">*</span>');
          }
          tr.append(hostnameCell);
      
      // Mfr column - show manufacturer override, or manufacturer discovered, or vendor (OUI)
      const mfr = row.manufacturer || row.vendor || '';
      tr.append($('<td data-column-id="vendor"></td>').text(mfr));
      
      tr.append($('<td data-column-id="device_type"></td>').text(row.device_type || ''));
      
      // Tags - parse if string (v1.7.0)
      let tags = row.tags || [];
      if (typeof tags === 'string' && tags) {
        try {
          tags = JSON.parse(tags);
        } catch(e) {
          tags = [];
        }
      }
      tr.append($('<td data-column-id="tags"></td>').text(Array.isArray(tags) ? tags.join(', ') : ''));
      tr.append($('<td data-column-id="model"></td>').text(row.model || ''));
      
      // OS column (v1.6.1) - show OS + version if available
      const osDisplay = (row.os || '') + (row.os_version ? (' ' + row.os_version) : '');
      tr.append($('<td data-column-id="os"></td>').text(osDisplay || ''));
      
      // mDNS services - parse if string (v1.7.0)
      let mdnsServices = row.mdns_services || [];
      if (typeof mdnsServices === 'string' && mdnsServices) {
        try {
          mdnsServices = JSON.parse(mdnsServices);
        } catch(e) {
          mdnsServices = [];
        }
      }
      tr.append($('<td data-column-id="mdns_services"></td>').text(Array.isArray(mdnsServices) ? mdnsServices.join(', ') : ''));
      
      // Open ports - show exhaustive if available, else quick scan (v2.0.3, v2.0.8 with service names)
      let exhaustivePorts = row.exhaustive_ports || [];
      if (typeof exhaustivePorts === 'string' && exhaustivePorts) {
        try {
          exhaustivePorts = JSON.parse(exhaustivePorts);
        } catch(e) {
          exhaustivePorts = [];
        }
      }
      
      // Use exhaustive ports if available, otherwise fall back to quick scan
      let displayPorts = [];
      if (Array.isArray(exhaustivePorts) && exhaustivePorts.length > 0) {
        displayPorts = exhaustivePorts;
      } else {
        let openPorts = row.open_ports || [];
        if (typeof openPorts === 'string' && openPorts) {
          try {
            openPorts = JSON.parse(openPorts);
          } catch(e) {
            openPorts = [];
          }
        }
        if (Array.isArray(openPorts)) {
          displayPorts = openPorts;
        }
      }
      
      tr.append($('<td data-column-id="open_ports"></td>').text(formatPorts(displayPorts)));
      tr.append($('<td data-column-id="snmp_sysname"></td>').text(row.snmp_sysname || ''));
      tr.append($('<td data-column-id="snmp_sysdescr"></td>').text(row.snmp_sysdescr || ''));
      tr.append($('<td data-column-id="interface"></td>').text(row.interface || ''));
      tr.append($('<td data-column-id="subnet"></td>').text(row.subnet || ''));
      
      // Via AP column (v2.0.0)
      const viaAp = row.ap_name || row.connected_to_ap || '';
      tr.append($('<td data-column-id="via_ap"></td>').text(viaAp));
      
          const lastSeen = row.last_seen ? new Date(row.last_seen * 1000).toLocaleString() : '';
      tr.append($('<td data-column-id="last_seen"></td>').text(lastSeen));
      
      // Edit button column (right edge)
      const editCell = $('<td></td>');
      const editBtn = $('<button class="btn btn-xs btn-default btn-edit-device" title="Edit"><i class="fa fa-pencil"></i></button>');
      editBtn.on('click', function(e) {
        e.stopPropagation();
        openEditModal(row);
      });
      editCell.append(editBtn);
      tr.append(editCell);
      
          tbody.append(tr);
        });
    
        $('#gridDevices tbody').remove();
        $('#gridDevices').append(tbody);
    
    // Apply column visibility to newly rendered rows
    applyColumnVisibility();
    
    // Update count display (v1.5.0 - dual filters, v2.0.9 - category filter)
    let filterParts = [];
    if (ndFlagFilter) filterParts.push('Flag: ' + ndFlagFilter);
    if (ndConnFilter) filterParts.push('Conn: ' + ndConnFilter);
    if (ndCategoryFilter) filterParts.push('Category: ' + ndCategoryFilter);
    const filterText = filterParts.length > 0 ? filterParts.join(' | ') : 'All';
    
    const countText = filtered.length === invData.length 
      ? `${filtered.length} devices` 
      : `${filtered.length} of ${invData.length} devices`;
    $('#nd_filter_state').text(filterText + ' | ' + countText);
    
    // Restore sort icon
    document.querySelectorAll('#gridDevices .nd-sortable-col i').forEach((icon)=>{
      icon.className = 'fa fa-sort';
    });
    const activeHeader = document.querySelector('#gridDevices .nd-sortable-col[data-column-id="' + invSortColumn + '"]');
    if (activeHeader) {
      const icon = activeHeader.querySelector('i');
      if (icon) {
        icon.className = invSortDir === 'asc' ? 'fa fa-sort-asc' : 'fa fa-sort-desc';
      }
    }
    
    updateBulkActions();
    console.log('Table rendered with', filtered.length, 'rows (of', invData.length, 'total)');
  }

  let currentDetailDevice = null;
  
  function openDetailModal(device) {
    currentDetailDevice = device;
    renderDetailView('current');
    
    // Ensure modal shows properly regardless of which tab is active (v2.0.10)
    // Move modal to body if not already there to avoid tab context issues
    const modal = $('#deviceDetailModal');
    if (modal.parent()[0] !== document.body) {
      modal.appendTo(document.body);
    }
    
    modal.modal({
      backdrop: true,
      keyboard: true,
      show: true
    });
    
    // Acknowledge device (clears lifecycle flags: new/changed/back)
    if (device.ip && device.lifecycle_flags) {
      $.ajax({
        url: '/api/netdiscover/acknowledge/device',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ip: device.ip}),
        success: function() {
          // Silently acknowledged - flags will clear on next scan
          // Update local data immediately for UI responsiveness
          device.lifecycle_flags = '';
          device.flag_acknowledged = 1;
        },
        error: function() {
          // Silent fail - not critical
        }
      });
    }
  }
  
  function renderDetailView(tab) {
    const device = currentDetailDevice;
    if (!device) return;
    
    let html = '';
    
    // Tab navigation
    html += '<ul class="nav nav-tabs" style="margin-bottom:12px;">';
    html += '<li class="' + (tab === 'current' ? 'active' : '') + '"><a href="#" data-tab="current">Current</a></li>';
    html += '<li class="' + (tab === 'history' ? 'active' : '') + '"><a href="#" data-tab="history">History</a></li>';
    html += '<li class="' + (tab === 'uptime' ? 'active' : '') + '"><a href="#" data-tab="uptime">Uptime</a></li>';
    html += '</ul>';
    
    if (tab === 'current') {
      html += '<table class="table table-condensed">';
      html += '<tr><th style="width:200px;">IP Address</th><td>' + (device.ip || '-') + '</td></tr>';
      html += '<tr><th>MAC Address</th><td>' + (device.mac || '-') + '</td></tr>';
      html += '<tr><th>Hostname</th><td>' + (device.hostname || '-');
      if (device.hostname_override) {
        html += ' <span class="label label-info">Custom</span>';
      }
      html += '</td></tr>';
      // Manufacturer (show override vs discovered) - v1.6.0
      html += '<tr><th>Manufacturer</th><td>';
      if (device.manufacturer && device.discovered_manufacturer && device.manufacturer !== device.discovered_manufacturer) {
        html += '<strong>' + device.manufacturer + '</strong> <span class="label label-info">Override</span><br>';
        html += '<span style="color:#888;font-size:90%;">Discovered: ' + device.discovered_manufacturer + '</span>';
      } else {
        html += (device.manufacturer || device.vendor || '-');
      }
      html += '</td></tr>';
      
      html += '<tr><th>Status</th><td>';
      html += 'Connection: <strong>' + (device.connection_state || 'online') + '</strong><br>';
      if (device.lifecycle_flags) {
        html += 'Flags: <span class="label label-warning">' + device.lifecycle_flags + '</span>';
      }
      html += '</td></tr>';
      
      html += '<tr><th>Device Type</th><td>' + (device.device_type || '-') + '</td></tr>';
      html += '<tr><th>Tags</th><td>' + ((device.tags || []).join(', ') || '-') + '</td></tr>';
      
      // Model (show override vs discovered) - v1.6.0
      html += '<tr><th>Model</th><td>';
      if (device.model && device.discovered_model && device.model !== device.discovered_model) {
        html += '<strong>' + device.model + '</strong> <span class="label label-info">Override</span><br>';
        html += '<span style="color:#888;font-size:90%;">Discovered: ' + device.discovered_model + '</span>';
      } else {
        html += (device.model || '-');
      }
      html += '</td></tr>';
      
      // Operating System - v1.6.0
      html += '<tr><th>Operating System</th><td>';
      const osDisplay = (device.os || '') + (device.os_version ? (' ' + device.os_version) : '');
      html += (osDisplay || '-');
      if (device.discovered_os && device.os && device.os !== device.discovered_os) {
        html += '<br><span style="color:#888;font-size:90%;">Discovered: ' + device.discovered_os + '</span>';
      }
      html += '</td></tr>';
      
      html += '<tr><th>Location</th><td>' + (device.location || '-') + '</td></tr>';
      
      // Network topology - v2.0.0
      if (device.connected_to_ap) {
        html += '<tr><th>Connected Via</th><td>';
        html += '<i class="fa fa-wifi"></i> WiFi Access Point<br>';
        html += '<strong>' + (device.ap_name || device.connected_to_ap) + '</strong>';
        if (device.ap_name && device.connected_to_ap !== device.ap_name) {
          html += ' (' + device.connected_to_ap + ')';
        }
        if (device.ap_last_seen) {
          const apSeenTime = new Date(device.ap_last_seen * 1000);
          const age = Math.floor((Date.now() / 1000 - device.ap_last_seen) / 60);
          html += '<br><span style="color:#888;font-size:90%;">Association confirmed ' + age + ' min ago</span>';
        }
        html += '</td></tr>';
      }
      
      html += '<tr><th>mDNS Services</th><td>' + ((device.mdns_services || []).join(', ') || '-') + '</td></tr>';
      
      // Open Ports with exhaustive scan option - v1.6.4 (fixed parsing)
      html += '<tr><th>Open Ports</th><td>';
      html += '<div style="display:flex;justify-content:space-between;align-items:start;gap:10px;">';
      html += '<div>';
      
      // Parse exhaustive_ports if it's a string
      let exhaustivePorts = device.exhaustive_ports;
      if (typeof exhaustivePorts === 'string' && exhaustivePorts) {
        try {
          exhaustivePorts = JSON.parse(exhaustivePorts);
        } catch(e) {
          exhaustivePorts = null;
        }
      }
      
      // Show exhaustive ports if available (v2.0.8 - with service names)
      if (exhaustivePorts && Array.isArray(exhaustivePorts) && exhaustivePorts.length > 0) {
        html += formatPorts(exhaustivePorts);
        if (device.exhaustive_ports_time) {
          const scanTime = new Date(device.exhaustive_ports_time * 1000).toLocaleString();
          html += '<br><span style="color:#888;font-size:90%;">Scanned: ' + scanTime + '</span>';
        }
      } else if (device.open_ports && device.open_ports.length > 0) {
        html += formatPorts(device.open_ports);
        html += '<br><span style="color:#888;font-size:90%;">Quick scan only</span>';
      } else {
        html += 'None detected';
      }
      
      html += '</div>';
      
      // Port scan controls (v2.0.7)
      html += '<div style="display:flex;flex-direction:column;gap:4px;min-width:200px;">';
      html += '<select class="form-control input-xs" id="port_range_select" style="font-size:11px;">';
      html += '<option value="1-1000">Top 1000 ports (fast)</option>';
      html += '<option value="1-10000">Top 10K ports</option>';
      html += '<option value="1-65535">All 65535 ports</option>';
      html += '<option value="custom">Custom range...</option>';
      html += '</select>';
      html += '<div id="custom_range_inputs" style="display:none;gap:4px;">';
      html += '<input type="number" class="form-control input-xs" id="port_start" placeholder="Start" min="1" max="65535" value="1" style="width:70px;font-size:11px;">';
      html += '<span style="padding:0 4px;">-</span>';
      html += '<input type="number" class="form-control input-xs" id="port_end" placeholder="End" min="1" max="65535" value="1000" style="width:70px;font-size:11px;">';
      html += '</div>';
      html += '<button class="btn btn-xs btn-warning" id="btn_port_scan" data-ip="' + (device.ip || '') + '">Scan Ports</button>';
      html += '</div>';
      
      html += '</div>';
      html += '<div id="port_scan_status" style="margin-top:8px;"></div>';
      html += '</td></tr>';
      html += '<tr><th>SNMP sysName</th><td>' + (device.snmp_sysname || '-') + '</td></tr>';
      html += '<tr><th>SNMP sysDescr</th><td>' + (device.snmp_sysdescr || '-') + '</td></tr>';
      html += '<tr><th>Interface</th><td>' + (device.interface || '-') + '</td></tr>';
      html += '<tr><th>Subnet</th><td>' + (device.subnet || '-') + '</td></tr>';
      html += '<tr><th>First Seen</th><td>' + (device.first_seen ? new Date(device.first_seen * 1000).toLocaleString() : '-') + '</td></tr>';
      html += '<tr><th>Last Seen</th><td>' + (device.last_seen ? new Date(device.last_seen * 1000).toLocaleString() : '-') + '</td></tr>';
      if (device.notes) {
        html += '<tr><th>Notes</th><td>' + device.notes + '</td></tr>';
      }
      html += '</table>';
    } else if (tab === 'history') {
      html += '<ul class="nav nav-pills" style="margin-bottom:15px;">';
      html += '<li class="active"><a href="#" data-view="timeline">Timeline</a></li>';
      html += '<li><a href="#" data-view="table">Table</a></li>';
      html += '</ul>';
      html += '<div id="history_timeline" style="display:block;"></div>';
      html += '<div id="history_table" style="display:none;"></div>';
      html += '<div id="history_loading">Loading history...</div>';
    } else if (tab === 'uptime') {
      html += '<div id="uptime_loading">Calculating uptime...</div>';
      html += '<div id="uptime_content" style="display:none;"></div>';
    }
    
    $('#device_detail_body').html(html);
    $('#btn_edit_from_detail').data('device', device);
    
    // Tab click handlers
    $('#device_detail_body').off('click', 'a[data-tab]');
    $('#device_detail_body').on('click', 'a[data-tab]', function(e) {
      e.preventDefault();
      renderDetailView($(this).data('tab'));
    });
    
    // History view switcher (timeline vs table)
    $('#device_detail_body').off('click', 'a[data-view]');
    $('#device_detail_body').on('click', 'a[data-view]', function(e) {
      e.preventDefault();
      const view = $(this).data('view');
      $(this).closest('ul').find('li').removeClass('active');
      $(this).parent().addClass('active');
      
      if (view === 'timeline') {
        $('#history_timeline').show();
        $('#history_table').hide();
      } else {
        $('#history_timeline').hide();
        $('#history_table').show();
      }
    });
    
    // Load data for tabs
    if (tab === 'history') {
      loadDeviceHistoryTimeline(device.ip);
      loadDeviceHistoryTable(device.ip);
    } else if (tab === 'uptime') {
      loadDeviceUptime(device.ip);
    }
  }
  
  function loadDeviceHistoryTimeline(ip) {
    // Load both timeline (connection states) and attribute changes (for markers)
    $.when(
      $.ajax({url: '/api/netdiscover/history/timeline?ip=' + encodeURIComponent(ip) + '&days=30', type: 'GET'}),
      $.ajax({url: '/api/netdiscover/history/device?ip=' + encodeURIComponent(ip), type: 'GET'})
    ).done(function(timelineResult, historyResult) {
      const timelineData = timelineResult[0];
      const historyData = historyResult[0];
      
      if (timelineData.error) {
        $('#history_timeline').html('<p class="text-danger">Error: ' + timelineData.error + '</p>');
        return;
      }
      
      const segments = timelineData.segments || [];
      const changes = (historyData.rows || []).filter(r => r.event_type === 'attribute_change');
      const startTime = timelineData.start_time;
      const endTime = timelineData.end_time;
      const totalDuration = endTime - startTime;
      
      let html = '<div style="padding:15px;">';
      html += '<h5>Connection State Timeline (Last 30 Days) - Most Recent on Left</h5>';
      
      // Date/time labels - REVERSED (most recent on left)
      html += '<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:90%;color:#888;">';
      html += '<span><strong>NOW</strong><br>' + new Date(endTime * 1000).toLocaleDateString() + '<br>' + new Date(endTime * 1000).toLocaleTimeString() + '</span>';
      html += '<span style="text-align:right;"><strong>30 DAYS AGO</strong><br>' + new Date(startTime * 1000).toLocaleDateString() + '<br>' + new Date(startTime * 1000).toLocaleTimeString() + '</span>';
      html += '</div>';
      
      // Timeline container with markers and clickable boundaries
      html += '<div style="position:relative;margin:20px 0;">';
      
      // Connection state bar with clickable boundaries - REVERSED
      html += '<div class="timeline-bar" style="display:flex;height:40px;border-radius:4px;overflow:visible;box-shadow:0 2px 4px rgba(0,0,0,0.2);position:relative;">';
      
      // Reverse segments array so most recent is first (left)
      const reversedSegments = segments.slice().reverse();
      let cumulativePercent = 0;
      
      reversedSegments.forEach(function(seg, idx) {
        // Connection state colors only
        let color = '#999';
        const connState = seg.status.split(',').pop().trim(); // Get connection part
        if (connState === 'online') color = '#5cb85c'; // green
        else if (connState === 'offline') color = '#f0ad4e'; // yellow
        else if (connState === 'missing') color = '#ff8c00'; // dark orange
        else if (connState === 'gone') color = '#d9534f'; // red
        
        const width = seg.percent || 0;
        const startDate = new Date(seg.start * 1000);
        const endDate = new Date(seg.end * 1000);
        const title = connState + ' (' + formatDuration(seg.duration) + ')\n' +
                     'From: ' + startDate.toLocaleString() + '\n' +
                     'To: ' + endDate.toLocaleString();
        
        html += '<div class="timeline-segment" data-idx="' + idx + '" data-start="' + seg.start + '" data-end="' + seg.end + '" ' +
                'style="width:' + width + '%;background:' + color + ';' +
                'border-right:1px solid rgba(255,255,255,0.3);position:relative;cursor:pointer;" title="' + title + '">';
        
        // Add clickable boundary marker at start (except first segment)
        if (idx > 0) {
          html += '<div class="timeline-boundary" style="position:absolute;left:0;top:-5px;width:2px;height:50px;background:#fff;cursor:pointer;' +
                  'box-shadow:0 0 4px rgba(0,0,0,0.5);" title="Click for details"></div>';
        }
        
        html += '</div>';
        cumulativePercent += width;
      });
      
      html += '</div>';
      
      // Attribute change markers (magenta diamonds) - REVERSED
      html += '<div style="position:relative;height:20px;margin-top:-20px;pointer-events:none;">';
      changes.forEach(function(change) {
        const changeTime = change.timestamp;
        // Reverse position: 100% - normal position (flip left-to-right)
        const normalPosition = ((changeTime - startTime) / totalDuration) * 100;
        const position = 100 - normalPosition;
        
        if (position >= 0 && position <= 100) {
          const tooltip = change.field_name + ' changed at ' + new Date(changeTime * 1000).toLocaleString();
          html += '<div style="position:absolute;left:' + position + '%;top:-10px;transform:translateX(-50%);" title="' + tooltip + '">';
          html += '<svg width="16" height="16"><path d="M 8,0 L 16,8 L 8,16 L 0,8 Z" fill="#ff00ff" stroke="#fff" stroke-width="1"/></svg>';
          html += '</div>';
        }
      });
      html += '</div>';
      
      // Detail popup area
      html += '<div id="timeline-detail" style="margin-top:10px;padding:10px;background:rgba(255,255,255,0.05);border-radius:4px;display:none;"></div>';
      
      html += '</div>'; // End timeline container
      
      // Legend
      html += '<div style="margin-top:20px;display:flex;gap:15px;flex-wrap:wrap;font-size:90%;">';
      html += '<strong>Connection States:</strong>';
      html += '<span><span style="display:inline-block;width:12px;height:12px;background:#5cb85c;border-radius:2px;margin:0 4px;"></span>Online</span>';
      html += '<span><span style="display:inline-block;width:12px;height:12px;background:#f0ad4e;border-radius:2px;margin:0 4px;"></span>Offline</span>';
      html += '<span><span style="display:inline-block;width:12px;height:12px;background:#ff8c00;border-radius:2px;margin:0 4px;"></span>Missing</span>';
      html += '<span><span style="display:inline-block;width:12px;height:12px;background:#d9534f;border-radius:2px;margin:0 4px;"></span>Gone</span>';
      html += '<span style="margin-left:15px;"><svg width="12" height="12" style="vertical-align:middle;margin:0 4px;"><path d="M 6,0 L 12,6 L 6,12 L 0,6 Z" fill="#ff00ff"/></svg>Attribute Change</span>';
      html += '</div>';
      
      html += '<div style="margin-top:10px;font-size:90%;">';
      html += '<strong>' + segments.length + '</strong> connection period(s), ';
      html += '<strong>' + changes.length + '</strong> attribute change(s) over <strong>' + timelineData.days + '</strong> days';
      html += '</div>';
      
      html += '</div>';
      
      $('#history_timeline').html(html);
      $('#history_loading').hide();
      
      // Add click handlers for timeline segments (v2.0.0 - works with reversed timeline)
      $('.timeline-segment').on('click', function() {
        const startTime = $(this).data('start');
        const endTime = $(this).data('end');
        
        // Data already in attributes, no need to look up in array
        const idx = $(this).data('idx');
        const startDate = new Date(startTime * 1000);
        const endDate = new Date(endTime * 1000);
        const duration = endTime - startTime;
        
        // Extract state from title (format: "state (duration)")
        const titleText = $(this).attr('title') || '';
        const connState = titleText.split('(')[0].trim();
        
        let detailHtml = '<strong>Period #' + (idx + 1) + ': ' + connState.toUpperCase() + '</strong><br>';
        detailHtml += '<strong>Started:</strong> ' + startDate.toLocaleString() + '<br>';
        detailHtml += '<strong>Ended:</strong> ' + endDate.toLocaleString() + '<br>';
        detailHtml += '<strong>Duration:</strong> ' + formatDuration(duration);
        
        $('#timeline-detail').html(detailHtml).show();
      });
      
      // Click diamond markers to show change details
      $('#history_timeline').on('click', 'svg', function(e) {
        e.stopPropagation();
        const title = $(this).parent().attr('title');
        if (title) {
          $('#timeline-detail').html('<strong>Attribute Change</strong><br>' + title).show();
        }
      });
      
    }).fail(function() {
      $('#history_timeline').html('<p class="text-danger">Error loading timeline</p>');
      $('#history_loading').hide();
    });
  }
  
  function loadDeviceHistoryTable(ip) {
    $.ajax({
      url: '/api/netdiscover/history/device?ip=' + encodeURIComponent(ip),
      type: 'GET',
      success: function(data) {
        const rows = data.rows || [];
        let html = '';
        
        if (rows.length === 0) {
          html = '<p class="text-muted">No history available. History tracking started in v1.1.0.</p>';
        } else {
          html = '<table class="table table-condensed table-hover">';
          html += '<thead><tr><th>Time</th><th>Event</th><th>Details</th></tr></thead><tbody>';
          
          rows.forEach(function(h) {
            const ts = h.timestamp ? new Date(h.timestamp * 1000).toLocaleString() : '';
            let eventText = h.event_type || '';
            let details = '';
            
            if (h.event_type === 'status_change') {
              eventText = 'Status Changed';
              details = (h.old_value || '?') + ' → ' + (h.new_value || '?');
            } else if (h.event_type === 'attribute_change') {
              eventText = h.field_name + ' Changed';
              details = (h.old_value || '?') + ' → ' + (h.new_value || '?');
            } else if (h.event_type === 'discovered') {
              eventText = 'First Discovered';
              details = h.details || '';
            }
            
            html += '<tr>';
            html += '<td style="white-space:nowrap;">' + ts + '</td>';
            html += '<td><strong>' + eventText + '</strong></td>';
            html += '<td>' + details + '</td>';
            html += '</tr>';
          });
          
          html += '</tbody></table>';
        }
        
        $('#history_table').html(html);
      },
      error: function() {
        $('#history_table').html('<p class="text-danger">Error loading history</p>');
      }
    });
  }
  
  function loadDeviceUptime(ip) {
    $.ajax({
      url: '/api/netdiscover/history/uptime?ip=' + encodeURIComponent(ip) + '&days=30',
      type: 'GET',
      success: function(data) {
        let html = '<div style="padding:20px;">';
        html += '<h4>Uptime Statistics (Last 30 Days)</h4>';
        html += '<div style="margin:20px 0;">';
        html += '<div style="font-size:48px;font-weight:bold;color:#5cb85c;">' + (data.uptime_percent || 0) + '%</div>';
        html += '<div class="text-muted">Uptime</div>';
        html += '</div>';
        html += '<table class="table table-condensed">';
        html += '<tr><th>Status Changes</th><td>' + (data.status_changes || 0) + '</td></tr>';
        html += '<tr><th>Total Downtime</th><td>' + formatDuration(data.downtime_seconds || 0) + '</td></tr>';
        html += '</table>';
        html += '</div>';
        
        $('#uptime_loading').hide();
        $('#uptime_content').html(html).show();
      },
      error: function() {
        $('#uptime_loading').html('<p class="text-danger">Error calculating uptime</p>');
      }
    });
  }
  
  function formatDuration(seconds) {
    if (seconds < 60) return seconds + ' sec';
    if (seconds < 3600) return Math.floor(seconds / 60) + ' min';
    if (seconds < 86400) return Math.floor(seconds / 3600) + ' hours';
    return Math.floor(seconds / 86400) + ' days';
  }
  
  // Port range dropdown handler (v2.0.7)
  $(document).on('change', '#port_range_select', function() {
    const customInputs = $('#custom_range_inputs');
    if ($(this).val() === 'custom') {
      customInputs.show();
    } else {
      customInputs.hide();
    }
  });
  
  // Port scan button handler (v1.6.0, updated v2.0.7 for custom ranges)
  $(document).on('click', '#btn_port_scan', function() {
    const ip = $(this).data('ip');
    const statusEl = $('#port_scan_status');
    const btn = $(this);
    
    // Determine port range
    let portRange = '';
    const rangeSelect = $('#port_range_select').val();
    
    if (rangeSelect === 'custom') {
      const startPort = parseInt($('#port_start').val()) || 1;
      const endPort = parseInt($('#port_end').val()) || 1000;
      
      if (startPort < 1 || startPort > 65535 || endPort < 1 || endPort > 65535 || startPort > endPort) {
        alert('Invalid port range. Ports must be between 1 and 65535, and start must be less than or equal to end.');
        return;
      }
      
      portRange = startPort + '-' + endPort;
    } else {
      portRange = rangeSelect;
    }
    
    // Parse range for display
    const rangeParts = portRange.split('-');
    const portCount = parseInt(rangeParts[1]) - parseInt(rangeParts[0]) + 1;
    
    // Estimate scan time
    let estimatedTime = '';
    if (portCount <= 1000) {
      estimatedTime = '30-60 seconds';
    } else if (portCount <= 10000) {
      estimatedTime = '2-4 minutes';
    } else {
      estimatedTime = '5-10 minutes';
    }
    
    if (!confirm('Run port scan on ' + ip + '?\n\nRange: ' + portRange + ' (' + portCount.toLocaleString() + ' ports)\nEstimated time: ' + estimatedTime + '\n\nNote: Port scan will be visible to IDS/IPS systems.')) {
      return;
    }
    
    btn.prop('disabled', true);
    $('#port_range_select').prop('disabled', true);
    statusEl.html('<div class="alert alert-info" style="color:#000;"><strong><i class="fa fa-spinner fa-spin"></i> Scanning ' + portCount.toLocaleString() + ' ports...</strong><br>Estimated time: ' + estimatedTime + '. Please wait.</div>');
    
    $.ajax({
      url: '/api/netdiscover/scan/ports',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({ip: ip, range: portRange}),
      timeout: 600000, // 10 minute timeout
      success: function(data) {
        if (data.status === 'success') {
          const count = data.count || 0;
          const ports = formatPorts(data.open_ports || []) || 'None';
          statusEl.html('<div class="alert alert-success" style="color:#000;"><strong><i class="fa fa-check"></i> Scan complete!</strong><br>' +
                       'Found <strong>' + count + '</strong> open port(s)<br>' +
                       (count > 0 ? '<strong>Ports:</strong> ' + ports : '<em>No open ports detected</em>') +
                       '</div>');
          
          // Reload device data and update detail modal (v2.0.8)
          $.ajax({
            url: '/api/netdiscover/inventory/search',
            type: 'POST',
            data: {current: 1, rowCount: 9999},
            success: function(response) {
              invData = response.rows || [];
              
              // Update current detail device with fresh data
              if (currentDetailDevice && currentDetailDevice.ip === ip) {
                const updatedDevice = invData.find(d => d.ip === ip);
                if (updatedDevice) {
                  currentDetailDevice = updatedDevice;
                  // Re-render the current tab to show new ports
                  renderDetailView('current');
                }
              }
              
              // Also reload table if we're on inventory tab
              if (typeof renderInventoryTable === 'function') {
                renderInventoryTable();
              }
            }
          });
        } else {
          // Check if device is offline (v2.0.12)
          if (data.offline) {
            statusEl.html('<div class="alert alert-warning" style="color:#000;"><strong><i class="fa fa-exclamation-triangle"></i> Device Offline</strong><br>' + 
                         (data.message || 'Device is not reachable') + 
                         '<br><br><em>The device has been marked as offline. Try again when the device is back online.</em></div>');
            
            // Reload device data to show updated offline status
            $.ajax({
              url: '/api/netdiscover/inventory/search',
              type: 'POST',
              data: {current: 1, rowCount: 9999},
              success: function(response) {
                invData = response.rows || [];
                
                // Update current detail device with fresh data
                if (currentDetailDevice && currentDetailDevice.ip === ip) {
                  const updatedDevice = invData.find(d => d.ip === ip);
                  if (updatedDevice) {
                    currentDetailDevice = updatedDevice;
                    renderDetailView('current');
                  }
                }
                
                if (typeof renderInventoryTable === 'function') {
                  renderInventoryTable();
                }
              }
            });
          } else {
            statusEl.html('<div class="alert alert-danger" style="color:#000;"><strong><i class="fa fa-exclamation-triangle"></i> Scan failed:</strong><br>' + (data.message || 'Unknown error') + '</div>');
          }
        }
      },
      error: function(xhr) {
        statusEl.html('<div class="alert alert-danger" style="color:#000;"><strong><i class="fa fa-exclamation-triangle"></i> Scan failed:</strong><br>' + (xhr.statusText || 'Network error') + '</div>');
      },
      complete: function() {
        btn.prop('disabled', false);
        $('#port_range_select').prop('disabled', false);
        setTimeout(function() {
          statusEl.html('');
        }, 10000);
      }
    });
  });
  
  $(document).on('click', '#btn_edit_from_detail', function() {
    const device = $(this).data('device');
    $('#deviceDetailModal').modal('hide');
    setTimeout(function() {
      openEditModal(device);
    }, 300);
  });

  function openEditModal(device) {
    $('#edit_ip').val(device.ip);
    $('#edit_ip_display').val(device.ip);
    $('#edit_mac_display').val(device.mac || '');
    $('#edit_hostname').val(device.hostname_override ? device.hostname : '');
    $('#edit_device_type').val(device.device_type || '');
    // Show custom manufacturer if set, otherwise show discovered (manufacturer OR vendor)
    const displayMfr = device.manufacturer_override ? device.manufacturer : (device.manufacturer || device.vendor || '');
    $('#edit_manufacturer').val(displayMfr);
    $('#edit_model').val(device.model || '');
    $('#edit_os').val(device.os || '');
    $('#edit_location').val(device.location || '');
    $('#edit_tags').val((device.tags || []).join(', '));
    $('#edit_notes').val(device.notes || '');
    
    // Ensure modal shows properly (v2.0.10)
    const modal = $('#editDeviceModal');
    if (modal.parent()[0] !== document.body) {
      modal.appendTo(document.body);
    }
    
    modal.modal('show');
  }

  $(document).on('click', '#btn_save_device', function() {
    const payload = {
      ip: $('#edit_ip').val(),
      hostname: $('#edit_hostname').val(),
      device_type: $('#edit_device_type').val(),
      manufacturer: $('#edit_manufacturer').val(),
      model: $('#edit_model').val(),
      os: $('#edit_os').val(),
      location: $('#edit_location').val(),
      tags: $('#edit_tags').val(),
      notes: $('#edit_notes').val()
    };
    
    $.ajax({
      url: '/api/netdiscover/overrides/set',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(payload),
      success: function(data) {
        console.log('Override saved:', data);
        $('#editDeviceModal').modal('hide');
        loadInventoryData(); // Reload table
      },
      error: function(xhr) {
        console.error('Override save failed:', xhr.status, xhr.responseText);
        alert('Failed to save: ' + (xhr.responseJSON?.error || xhr.responseText));
      }
    });
  });

  $(document).on('click', '#btn_delete_override', function() {
    const ip = $('#edit_ip').val();
    if (confirm('Clear all custom settings for ' + ip + '?')) {
      $.ajax({
        url: '/api/netdiscover/overrides/delete',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ip: ip}),
        success: function(data) {
          console.log('Override deleted:', data);
          $('#editDeviceModal').modal('hide');
          loadInventoryData(); // Reload table
        },
        error: function(xhr) {
          console.error('Override delete failed:', xhr.status, xhr.responseText);
        }
      });
    }
  });
  
  // Delete device button - show confirmation modal
  $(document).on('click', '#btn_delete_device', function() {
    const ip = $('#edit_ip').val();
    $('#delete_confirm_ip').text(ip);
    $('#btn_confirm_delete').data('ip', ip);
    $('#editDeviceModal').modal('hide');
    $('#deleteConfirmModal').modal('show');
  });
  
  // Confirm delete - actually delete the device
  $(document).on('click', '#btn_confirm_delete', function() {
    const ip = $(this).data('ip');
    
    $.ajax({
      url: '/api/netdiscover/inventory/delete',
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({ip: ip}),
      success: function(data) {
        console.log('Device deleted:', data);
        $('#deleteConfirmModal').modal('hide');
        loadInventoryData(); // Reload table
        alert('Device ' + ip + ' has been deleted from inventory');
      },
      error: function(xhr) {
        console.error('Device delete failed:', xhr.status, xhr.responseText);
        $('#deleteConfirmModal').modal('hide');
        alert('Failed to delete device: ' + (xhr.responseJSON?.error || xhr.responseText));
      }
    });
  });
  
  // Bulk tag button
  $(document).on('click', '#btn_bulk_tag', function() {
    $('#bulk_tag_count').text(selectedDevices.size);
    $('#bulk_tags_input').val('');
    $('#bulkTagModal').modal('show');
  });
  
  // Bulk tag save
  $(document).on('click', '#btn_bulk_tag_save', function() {
    const tags = $('#bulk_tags_input').val();
    const ips = Array.from(selectedDevices);
    
    if (!tags.trim()) {
      alert('Please enter at least one tag');
      return;
    }
    
    let completed = 0;
    const total = ips.length;
    
    ips.forEach(function(ip) {
      // Find device to preserve existing data
      const device = invData.find(d => d.ip === ip);
      if (!device) return;
      
      const payload = {
        ip: ip,
        hostname: device.hostname_override ? device.hostname : '',
        device_type: device.device_type || '',
        manufacturer: device.manufacturer || '',
        model: device.model || '',
        location: device.location || '',
        tags: tags,
        notes: device.notes || ''
      };
      
      $.ajax({
        url: '/api/netdiscover/overrides/set',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(payload),
        success: function() {
          completed++;
          if (completed === total) {
            $('#bulkTagModal').modal('hide');
            selectedDevices.clear();
            updateBulkActions();
            loadInventoryData();
            alert('Tagged ' + total + ' device(s) successfully');
          }
        },
        error: function(xhr) {
          console.error('Bulk tag failed for ' + ip, xhr.responseText);
        }
      });
    });
  });
  
  // Bulk delete button
  $(document).on('click', '#btn_bulk_delete', function() {
    const count = selectedDevices.size;
    if (!confirm('Clear custom settings for ' + count + ' selected device(s)?')) {
      return;
    }
    
    const ips = Array.from(selectedDevices);
    let completed = 0;
    
    ips.forEach(function(ip) {
      $.ajax({
        url: '/api/netdiscover/overrides/delete',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ip: ip}),
        success: function() {
          completed++;
          if (completed === ips.length) {
            selectedDevices.clear();
            updateBulkActions();
            loadInventoryData();
            alert('Cleared overrides for ' + ips.length + ' device(s)');
          }
        },
        error: function(xhr) {
          console.error('Bulk delete failed for ' + ip, xhr.responseText);
        }
      });
    });
  });

  $('a[href="#tab_inv"]').on('shown.bs.tab', function() {
    console.log('Inventory tab shown, initialized=' + inventoryGridInitialized);
    if (!inventoryGridInitialized) {
      console.log('Loading inventory data...');
      setTimeout(loadInventoryData, 100);
      inventoryGridInitialized = true;
    }
    
    // Start auto-refresh when tab is shown
    if (!inventoryRefreshInterval) {
      inventoryRefreshInterval = setInterval(function() {
        console.log('Auto-refreshing inventory...');
        loadInventoryData();
      }, REFRESH_INTERVAL_MS);
    }
  });
  
  $('a[href="#tab_inv"]').on('hidden.bs.tab', function() {
    // Stop auto-refresh when leaving tab
    if (inventoryRefreshInterval) {
      clearInterval(inventoryRefreshInterval);
      inventoryRefreshInterval = null;
    }
  });

  // Default tab is inventory; populate it immediately so first load is not blank.
  if (!inventoryGridInitialized) {
    loadInventoryData();
    inventoryGridInitialized = true;
    
    // Start auto-refresh for default tab
    inventoryRefreshInterval = setInterval(function() {
      console.log('Auto-refreshing inventory...');
      loadInventoryData();
    }, REFRESH_INTERVAL_MS);
  }

  let eventsSearchTerm = '';
  let eventsSortColumn = 'time';
  let eventsSortDir = 'desc';
  let eventsData = [];
  let eventsGroupFilter = localStorage.getItem('nd_events_group_filter') || 'all';
  
  // IP address sorting helper - converts IP to comparable number
  function ipToNumber(ip) {
    if (!ip || typeof ip !== 'string') return 0;
    const parts = ip.split('.');
    if (parts.length !== 4) return 0;
    return (parseInt(parts[0]) * 16777216) + 
           (parseInt(parts[1]) * 65536) + 
           (parseInt(parts[2]) * 256) + 
           parseInt(parts[3]);
  }

  function loadEventsData() {
    const refreshBtn = document.getElementById('btn_refresh_events');
    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.querySelector('i').classList.add('fa-spin');
    }
    
    $.ajax({
      url: '/api/netdiscover/events/search',
      type: 'POST',
      data: {current: 1, rowCount: 9999},
      success: function(response) {
        console.log('Events loaded:', response.rows.length, 'events');
        eventsData = response.rows;
        renderEventsTable();
        
        // Update last update timestamp
        const updateEl = document.getElementById('events_last_update');
        if (updateEl) {
          updateEl.textContent = 'Updated: ' + new Date().toLocaleTimeString();
        }
      },
      error: function(xhr) {
        console.error('Events load failed:', xhr.status, xhr.responseText);
      },
      complete: function() {
        if (refreshBtn) {
          refreshBtn.disabled = false;
          refreshBtn.querySelector('i').classList.remove('fa-spin');
        }
      }
    });
  }
  
  // Manual refresh button
  const btnRefreshEvents = document.getElementById('btn_refresh_events');
  if (btnRefreshEvents) {
    btnRefreshEvents.addEventListener('click', function() {
      loadEventsData();
    });
  }
  
  function renderEventsTable() {
    let filtered = eventsData.slice();
    
    // Apply group filter (latest per device)
    if (eventsGroupFilter === 'latest') {
      const latestByDevice = new Map();
      filtered.forEach(function(row) {
        const ip = row.ip || '';
        if (!ip) return;
        
        // Keep only the event with the latest timestamp for each IP
        const existing = latestByDevice.get(ip);
        if (!existing || (row.time || 0) > (existing.time || 0)) {
          latestByDevice.set(ip, row);
        }
      });
      filtered = Array.from(latestByDevice.values());
    }
    
    // Apply search filter
    if (eventsSearchTerm) {
      filtered = filtered.filter(function(row) {
        const searchable = [
          row.type || '',
          row.ip || '',
          row.mac || '',
          row.hostname || '',
          JSON.stringify(row.details || {})
        ].join(' ').toLowerCase();
        return searchable.indexOf(eventsSearchTerm) !== -1;
      });
    }
    
    // Apply sorting
    filtered.sort(function(a, b) {
      let aVal = a[eventsSortColumn] || '';
      let bVal = b[eventsSortColumn] || '';
      
      // Special handling for IP addresses (numeric per octet)
      if (eventsSortColumn === 'ip') {
        aVal = ipToNumber(aVal);
        bVal = ipToNumber(bVal);
        const cmp = aVal - bVal;
        return eventsSortDir === 'asc' ? cmp : -cmp;
      }
      
      // Special handling for time (numeric)
      if (eventsSortColumn === 'time') {
        aVal = parseInt(aVal) || 0;
        bVal = parseInt(bVal) || 0;
        const cmp = aVal - bVal;
        return eventsSortDir === 'asc' ? cmp : -cmp;
      }
      
      // String comparison
      aVal = String(aVal).toLowerCase();
      bVal = String(bVal).toLowerCase();
      
      if (aVal < bVal) return eventsSortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return eventsSortDir === 'asc' ? 1 : -1;
      return 0;
    });
    
    // Render rows
        const tbody = $('<tbody></tbody>');
    filtered.forEach(function(row) {
          const tr = $('<tr></tr>');
          tr.data('event', row);
          
          // Make row clickable to view device details
          tr.css('cursor', 'pointer');
          tr.on('click', function(e) {
            if (!$(e.target).is('input, button, a')) {
              // Find the device in inventory by IP
              const eventIp = row.ip;
              if (eventIp) {
                // If inventory data is not loaded yet, load it first
                if (invData.length === 0) {
                  // Show loading indicator
                  const loadingMsg = $('<div class="alert alert-info" style="margin:10px;">Loading device details...</div>');
                  $(this).after(loadingMsg);
                  
                  // Load inventory data
                  $.ajax({
                    url: '/api/netdiscover/inventory/search',
                    type: 'POST',
                    data: {current: 1, rowCount: 9999},
                    success: function(response) {
                      invData = response.rows || [];
                      const device = invData.find(d => d.ip === eventIp);
                      loadingMsg.remove();
                      
                      if (device) {
                        openDetailModal(device);
                      } else {
                        alert('Device ' + eventIp + ' not found in current inventory. It may have been removed or is filtered out.');
                      }
                    },
                    error: function() {
                      loadingMsg.remove();
                      alert('Failed to load device details. Please try again.');
                    }
                  });
                } else {
                  // Inventory already loaded, find device
                  const device = invData.find(d => d.ip === eventIp);
                  if (device) {
                    openDetailModal(device);
                  } else {
                    // Device not in current inventory (maybe filtered out or gone)
                    alert('Device ' + eventIp + ' not found in current inventory. It may have been removed or is filtered out.');
                  }
                }
              }
            }
          });
          
          const time = row.time ? new Date(row.time * 1000).toLocaleString() : '';
          tr.append($('<td></td>').text(time));
      
      // Type column with colored indicator - v1.4.0 colors
      const typeCell = $('<td></td>');
      const type = row.type || row.event_type || '';
      let color = '#999'; // default gray
      if (type === 'new') color = '#f0ad4e'; // orange
      else if (type === 'up') color = '#5cb85c'; // green
      else if (type === 'back') color = '#5bc0de'; // cyan
      else if (type === 'changed') color = '#428bca'; // light blue
      else if (type === 'offline') color = '#f0ad4e'; // yellow/orange
      else if (type === 'gone') color = '#d9534f'; // red
      
      const indicator = $('<span style="display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;"></span>').css('background-color', color);
      typeCell.append(indicator);
      typeCell.append(document.createTextNode(type));
      tr.append(typeCell);
      
          tr.append($('<td></td>').text(row.ip || ''));
          tr.append($('<td></td>').text(row.mac || ''));
          tr.append($('<td></td>').text(row.hostname || ''));
          tr.append($('<td></td>').text(JSON.stringify(row.details || {})));
          tbody.append(tr);
        });
    
        $('#gridEvents tbody').remove();
        $('#gridEvents').append(tbody);
    
    // Update count display
    let countText = '';
    if (eventsGroupFilter === 'latest') {
      countText = `${filtered.length} device(s) (latest event per device)`;
    } else if (filtered.length === eventsData.length) {
      countText = `${filtered.length} event(s)`;
    } else {
      countText = `${filtered.length} of ${eventsData.length} event(s)`;
    }
    
    // Update or create count display element
    let countEl = document.getElementById('nd_events_count');
    if (!countEl) {
      countEl = document.createElement('div');
      countEl.id = 'nd_events_count';
      countEl.style.cssText = 'margin-top:8px;color:#888;font-size:90%;';
      const eventsTable = document.getElementById('gridEvents');
      if (eventsTable && eventsTable.parentNode) {
        eventsTable.parentNode.appendChild(countEl);
      }
    }
    if (countEl) {
      countEl.textContent = countText;
    }
    
    console.log('Events table rendered with', filtered.length, 'rows (of', eventsData.length, 'total)', eventsGroupFilter === 'latest' ? '(latest per device)' : '');
  }

  function updateEventsFilterState() {
    // Update group filter buttons
    document.querySelectorAll('.nd-filter-event-group').forEach((b)=>{
      const btnGroup = b.getAttribute('data-group') || 'all';
      if (btnGroup === eventsGroupFilter) {
        b.classList.add('btn-primary');
        b.classList.remove('btn-default');
      } else {
        b.classList.remove('btn-primary');
        b.classList.add('btn-default');
      }
    });
  }

  $('a[href="#tab_events"]').on('shown.bs.tab', function() {
    console.log('Events tab shown, initialized=' + eventsGridInitialized);
    if (!eventsGridInitialized) {
      console.log('Loading events data...');
      setTimeout(loadEventsData, 100);
      eventsGridInitialized = true;
      
      // Setup search box
      const eventsSearchInput = document.getElementById('events_search');
      if (eventsSearchInput) {
        eventsSearchInput.addEventListener('input', function() {
          eventsSearchTerm = this.value.toLowerCase();
          renderEventsTable();
        });
      }
      
      const eventsSearchClear = document.getElementById('events_search_clear');
      if (eventsSearchClear) {
        eventsSearchClear.addEventListener('click', function() {
          if (eventsSearchInput) {
            eventsSearchInput.value = '';
            eventsSearchTerm = '';
            renderEventsTable();
          }
        });
      }
      
      // Group filter buttons (all vs latest per device)
      document.querySelectorAll('.nd-filter-event-group').forEach((btn)=>{
        btn.addEventListener('click', ()=>{
          eventsGroupFilter = btn.getAttribute('data-group') || 'all';
          localStorage.setItem('nd_events_group_filter', eventsGroupFilter);
          updateEventsFilterState();
          renderEventsTable();
        });
      });
      
      // Restore filter state on load
      updateEventsFilterState();
      
      // Column sorting for events
      document.querySelectorAll('#gridEvents .nd-sortable-col').forEach((th)=>{
        th.addEventListener('click', function(e) {
          // Don't sort if clicking on resize handle
          if (e.target.classList.contains('nd-resize-handle')) return;
          
          const col = this.getAttribute('data-column-id');
          if (eventsSortColumn === col) {
            eventsSortDir = (eventsSortDir === 'asc') ? 'desc' : 'asc';
          } else {
            eventsSortColumn = col;
            eventsSortDir = 'desc'; // Default to desc for events (most recent first)
          }
          
          // Update sort icons
          document.querySelectorAll('#gridEvents .nd-sortable-col i').forEach((icon)=>{
            icon.className = 'fa fa-sort';
          });
          const icon = this.querySelector('i');
          if (icon) {
            icon.className = eventsSortDir === 'asc' ? 'fa fa-sort-asc' : 'fa fa-sort-desc';
          }
          
          renderEventsTable();
        });
      });
      
      // Column resizing for events
      document.querySelectorAll('#gridEvents .nd-resize-handle').forEach((handle)=>{
        handle.addEventListener('mousedown', function(e) {
          e.preventDefault();
          e.stopPropagation();
          
          const column = this.parentElement;
          const startX = e.pageX;
          const startWidth = column.offsetWidth;
          
          function onResize(e) {
            const diff = e.pageX - startX;
            const newWidth = Math.max(50, startWidth + diff);
            column.style.width = newWidth + 'px';
          }
          
          function stopResize() {
            const colId = column.getAttribute('data-column-id');
            const width = column.offsetWidth;
            localStorage.setItem('nd_events_col_width_' + colId, width);
            document.removeEventListener('mousemove', onResize);
            document.removeEventListener('mouseup', stopResize);
          }
          
          document.addEventListener('mousemove', onResize);
          document.addEventListener('mouseup', stopResize);
        });
      });
      
      // Restore saved column widths for events
      document.querySelectorAll('#gridEvents .nd-resizable-col').forEach((th)=>{
        const colId = th.getAttribute('data-column-id');
        const savedWidth = localStorage.getItem('nd_events_col_width_' + colId);
        if (savedWidth) {
          th.style.width = savedWidth + 'px';
        }
      });
    }
    
    // Start auto-refresh when tab is shown
    if (!eventsRefreshInterval) {
      eventsRefreshInterval = setInterval(function() {
        console.log('Auto-refreshing events...');
        loadEventsData();
      }, REFRESH_INTERVAL_MS);
    }
  });
  
  $('a[href="#tab_events"]').on('hidden.bs.tab', function() {
    // Stop auto-refresh when leaving tab
    if (eventsRefreshInterval) {
      clearInterval(eventsRefreshInterval);
      eventsRefreshInterval = null;
    }
  });

  }); // end document ready
})();
