<div class="content-box">
  <div class="pull-right">
    <span class="label label-default" style="margin-right:8px;">v2.1.2</span>
    <button class="btn btn-xs btn-primary" id="btn_save"><i class="fa fa-save"></i> Save</button>
    <button class="btn btn-xs btn-default" id="btn_apply"><i class="fa fa-play"></i> Apply</button>
  </div>

  <h1>NetDiscover</h1>
  <p>*ing-like device discovery across multiple VLANs/subnets (dnsmasq + SSDP + mDNS + LLMNR/NBNS + optional probes/SNMP).</p>

  <div id="saveMsg" class="alert alert-info" style="display:none" role="alert">
    Settings saved. Click <b>Apply</b> to reconfigure + restart the service.
  </div>

  <ul class="nav nav-tabs" role="tablist" style="margin-top:12px;">
    <li class="active"><a href="#tab_inv" role="tab" data-toggle="tab">Inventory</a></li>
    <li><a href="#tab_events" role="tab" data-toggle="tab">Recent Changes</a></li>
    <li><a href="#tab_settings" role="tab" data-toggle="tab">Settings</a></li>
  </ul>

  <div class="tab-content" style="margin-top:12px;">
    <div class="tab-pane active" id="tab_inv">
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;align-items:center;">
        <div class="btn-group btn-group-xs" role="group" aria-label="Lifecycle filter">
          <button class="btn btn-default nd-filter-flag" data-flag="">All</button>
          <button class="btn btn-default nd-filter-flag" data-flag="new">New</button>
          <button class="btn btn-default nd-filter-flag" data-flag="changed">Changed</button>
          <button class="btn btn-default nd-filter-flag" data-flag="back">Back</button>
        </div>
        <span style="color:#666;">|</span>
        <div class="btn-group btn-group-xs" role="group" aria-label="Connection filter">
          <button class="btn btn-default nd-filter-conn" data-conn="">All</button>
          <button class="btn btn-default nd-filter-conn" data-conn="online">Online</button>
          <button class="btn btn-default nd-filter-conn" data-conn="offline">Offline</button>
          <button class="btn btn-default nd-filter-conn" data-conn="missing">Missing</button>
          <button class="btn btn-default nd-filter-conn" data-conn="gone">Gone</button>
        </div>
        <span style="color:#666;">|</span>
        <div class="btn-group btn-group-xs" role="group" aria-label="Category filter">
          <button class="btn btn-default nd-filter-category" data-category="" title="All device categories">All</button>
          <button class="btn btn-default nd-filter-category" data-category="Network" title="Routers, switches, APs"><i class="fa fa-sitemap"></i></button>
          <button class="btn btn-default nd-filter-category" data-category="Computer" title="Desktops, laptops, servers"><i class="fa fa-desktop"></i></button>
          <button class="btn btn-default nd-filter-category" data-category="Mobile" title="Phones, tablets"><i class="fa fa-mobile"></i></button>
          <button class="btn btn-default nd-filter-category" data-category="Printer" title="Printers, MFPs"><i class="fa fa-print"></i></button>
          <button class="btn btn-default nd-filter-category" data-category="Storage" title="NAS, storage devices"><i class="fa fa-hdd-o"></i></button>
          <button class="btn btn-default nd-filter-category" data-category="Camera" title="IP cameras, NVRs"><i class="fa fa-video-camera"></i></button>
          <button class="btn btn-default nd-filter-category" data-category="Media" title="TVs, streaming devices"><i class="fa fa-tv"></i></button>
          <button class="btn btn-default nd-filter-category" data-category="IoT" title="Smart home, IoT devices"><i class="fa fa-lightbulb-o"></i></button>
        </div>
        <div class="input-group input-group-sm" style="width:300px;">
          <span class="input-group-addon"><i class="fa fa-search"></i></span>
          <input type="text" class="form-control" id="inv_search" placeholder="Search IP, MAC, hostname, vendor...">
          <span class="input-group-btn">
            <button class="btn btn-default" id="inv_search_clear"><i class="fa fa-times"></i></button>
          </span>
        </div>
        <button class="btn btn-xs btn-default" id="btn_export_csv"><i class="fa fa-download"></i> Export CSV</button>
        <button class="btn btn-xs btn-default" id="btn_refresh_inv" title="Refresh Now"><i class="fa fa-refresh"></i></button>
        <button class="btn btn-xs btn-default" id="btn_columns_inv" title="Show/Hide Columns"><i class="fa fa-columns"></i> Columns</button>
        <button class="btn btn-xs btn-info" id="btn_status_legend" title="Status Legend"><i class="fa fa-question-circle"></i> Legend</button>
        <div class="btn-group btn-group-xs" id="bulk_actions" style="display:none;">
          <button class="btn btn-warning" id="btn_bulk_tag"><i class="fa fa-tag"></i> Tag Selected</button>
          <button class="btn btn-danger" id="btn_bulk_delete"><i class="fa fa-trash"></i> Clear Overrides</button>
        </div>
        <span class="text-muted" id="nd_filter_state" style="align-self:center;"></span>
        <span class="text-muted" id="nd_selected_count" style="align-self:center;display:none;font-weight:bold;"></span>
        <span class="text-muted" id="inv_last_update" style="align-self:center;font-size:90%;"></span>
      </div>
      <div style="overflow-x:auto;">
        <table id="gridDevices" class="table table-condensed table-hover table-striped nd-sortable nd-resizable" data-editDialog="false">
          <thead>
            <tr>
              <th data-column-id="select" style="width:35px;min-width:35px;">
                <input type="checkbox" id="select_all_devices" title="Select All">
              </th>
              <th data-column-id="view" style="width:50px;min-width:50px;">
                <div class="nd-th-content">View</div>
              </th>
              <th data-column-id="flags" class="nd-sortable-col" style="width:45px;min-width:45px;" 
                  title="Lifecycle: 🟠 New | 🔷 Changed | 🔵 Back">
                <div class="nd-th-content" style="flex-direction:column;gap:2px;">
                  <div style="display:flex;gap:2px;">
                    <span style="width:8px;height:8px;border-radius:50%;background:#f0ad4e;" title="New"></span>
                    <span style="width:8px;height:8px;border-radius:50%;background:#428bca;" title="Changed"></span>
                    <span style="width:8px;height:8px;border-radius:50%;background:#5bc0de;" title="Back"></span>
                  </div>
                  <i class="fa fa-flag" style="font-size:10px;opacity:0.6;" title="Lifecycle Flags"></i>
                </div>
              </th>
              <th data-column-id="connection" class="nd-sortable-col" style="width:45px;min-width:45px;"
                  title="Connection: 🟢 Online | 🟡 Offline | 🟠 Missing | 🔴 Gone">
                <div class="nd-th-content" style="flex-direction:column;gap:2px;">
                  <div style="display:flex;gap:2px;">
                    <span style="width:8px;height:8px;border-radius:50%;background:#5cb85c;" title="Online"></span>
                    <span style="width:8px;height:8px;border-radius:50%;background:#f0ad4e;" title="Offline"></span>
                    <span style="width:8px;height:8px;border-radius:50%;background:#ff8c00;" title="Missing"></span>
                    <span style="width:8px;height:8px;border-radius:50%;background:#d9534f;" title="Gone"></span>
                  </div>
                  <i class="fa fa-circle" style="font-size:10px;opacity:0.6;" title="Connection State"></i>
                </div>
              </th>
              <th data-column-id="ip" class="nd-sortable-col nd-resizable-col" data-sort-dir="asc" style="width:120px;min-width:100px;">
                <div class="nd-th-content">IP <i class="fa fa-sort-asc"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="dhcp" class="nd-sortable-col" style="width:35px;min-width:35px;" 
                  title="DHCP Type: 🔵 Static | 🟡 Reserved | 🟢 Dynamic">
                <div class="nd-th-content" style="flex-direction:column;gap:2px;">
                  <div style="display:flex;gap:2px;">
                    <span style="width:6px;height:6px;border-radius:50%;background:#5bc0de;" title="Static"></span>
                    <span style="width:6px;height:6px;border-radius:50%;background:#f0ad4e;" title="Reserved"></span>
                    <span style="width:6px;height:6px;border-radius:50%;background:#5cb85c;" title="Dynamic"></span>
                  </div>
                  <i class="fa fa-exchange" style="font-size:9px;opacity:0.6;" title="DHCP Type"></i>
                </div>
              </th>
              <th data-column-id="mac" class="nd-sortable-col nd-resizable-col" style="width:140px;min-width:120px;">
                <div class="nd-th-content">MAC <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="hostname" class="nd-sortable-col nd-resizable-col" style="width:180px;min-width:100px;">
                <div class="nd-th-content">Hostname <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="vendor" class="nd-sortable-col nd-resizable-col" style="width:140px;min-width:80px;">
                <div class="nd-th-content">Mfr <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="device_type" class="nd-sortable-col nd-resizable-col" style="width:100px;min-width:80px;">
                <div class="nd-th-content">Type <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="tags" class="nd-resizable-col" style="width:120px;min-width:80px;">
                <div class="nd-th-content">Tags</div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="model" class="nd-sortable-col nd-resizable-col" style="width:120px;min-width:80px;">
                <div class="nd-th-content">Model <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="os" class="nd-sortable-col nd-resizable-col" style="width:140px;min-width:100px;">
                <div class="nd-th-content">OS <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="mdns_services" class="nd-resizable-col" style="width:150px;min-width:80px;">
                <div class="nd-th-content">mDNS Services</div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="open_ports" class="nd-resizable-col" style="width:100px;min-width:70px;">
                <div class="nd-th-content">Ports</div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="snmp_sysname" class="nd-sortable-col nd-resizable-col" style="width:120px;min-width:80px;">
                <div class="nd-th-content">SNMP sysName <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="snmp_sysdescr" class="nd-sortable-col nd-resizable-col" style="width:150px;min-width:100px;">
                <div class="nd-th-content">SNMP sysDescr <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="interface" class="nd-sortable-col nd-resizable-col" style="width:100px;min-width:70px;">
                <div class="nd-th-content">Interface <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="subnet" class="nd-sortable-col nd-resizable-col" style="width:120px;min-width:90px;">
                <div class="nd-th-content">Subnet <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="via_ap" class="nd-sortable-col nd-resizable-col" style="width:120px;min-width:80px;">
                <div class="nd-th-content"><i class="fa fa-wifi"></i> Via AP <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="last_seen" class="nd-sortable-col nd-resizable-col" data-sort-type="number" style="width:150px;min-width:120px;">
                <div class="nd-th-content">Last Seen <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="edit" style="width:50px;min-width:50px;">
                <div class="nd-th-content">Edit</div>
              </th>
            </tr>
          </thead>
        </table>
      </div>

      <!-- Status Legend Modal -->
      <div class="modal fade" id="statusLegendModal" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
              <h4 class="modal-title">Status Indicators Legend</h4>
            </div>
            <div class="modal-body">
              <div class="row">
                <div class="col-md-6">
                  <h5><i class="fa fa-flag"></i> Lifecycle Flags</h5>
                  <p class="text-muted">Temporary markers (cleared after 24h or when reviewed):</p>
                  <ul class="list-unstyled" style="line-height:2;">
                    <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f0ad4e;margin-right:8px;"></span> <strong>New</strong> - First discovered</li>
                    <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#428bca;margin-right:8px;"></span> <strong>Changed</strong> - Attributes modified</li>
                    <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#5bc0de;margin-right:8px;"></span> <strong>Back</strong> - Returned online</li>
                  </ul>
                  <p class="text-muted" style="font-size:90%;"><em>Multiple flags can appear simultaneously</em></p>
                </div>
                <div class="col-md-6">
                  <h5><i class="fa fa-circle"></i> Connection State</h5>
                  <p class="text-muted">Current network connectivity:</p>
                  <ul class="list-unstyled" style="line-height:2;">
                    <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#5cb85c;margin-right:8px;"></span> <strong>Online</strong> - Currently reachable</li>
                    <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f0ad4e;margin-right:8px;"></span> <strong>Offline</strong> - Not seen for 2+ scans</li>
                    <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ff8c00;margin-right:8px;"></span> <strong>Missing</strong> - Not seen for 30 days</li>
                    <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#d9534f;margin-right:8px;"></span> <strong>Gone</strong> - Not seen for 60 days</li>
                  </ul>
                  <p class="text-muted" style="font-size:90%;"><em>Only one connection state at a time</em></p>
                </div>
              </div>
              <hr>
              <div class="row">
                <div class="col-md-12">
                  <h5><i class="fa fa-exchange"></i> DHCP Type</h5>
                  <p class="text-muted">IP address assignment method:</p>
                  <ul class="list-unstyled" style="line-height:2;">
                    <li><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#5bc0de;margin-right:8px;"></span> <strong>Static</strong> - Outside DHCP range</li>
                    <li><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f0ad4e;margin-right:8px;"></span> <strong>Reserved</strong> - MAC-based DHCP reservation</li>
                    <li><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#5cb85c;margin-right:8px;"></span> <strong>Dynamic</strong> - Regular DHCP lease</li>
                    <li><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#999;margin-right:8px;"></span> <strong>Unknown</strong> - Could not determine</li>
                  </ul>
                </div>
              </div>
              <hr>
              <h5>Examples:</h5>
              <ul style="line-height:2;">
                <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f0ad4e;margin-right:4px;"></span> + <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#5cb85c;margin-left:4px;margin-right:8px;"></span> = <strong>New device that is online</strong></li>
                <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#428bca;margin-right:4px;"></span> + <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#5cb85c;margin-left:4px;margin-right:8px;"></span> = <strong>Hostname changed on online device</strong></li>
                <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#5bc0de;margin-right:4px;"></span> + <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#5cb85c;margin-left:4px;margin-right:8px;"></span> = <strong>Just came back online</strong></li>
                <li><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f0ad4e;margin-right:8px;"></span> (no flag) = <strong>Device temporarily offline</strong></li>
              </ul>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-primary" data-dismiss="modal">Close</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Column Configuration Modal -->
      <div class="modal fade" id="columnConfigModal" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
              <h4 class="modal-title">Configure Columns</h4>
            </div>
            <div class="modal-body">
              <p class="text-muted">Show or hide columns in the Inventory table:</p>
              <div class="row">
                <div class="col-md-6">
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="mac" checked> MAC Address</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="hostname" checked> Hostname</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="vendor" checked> Manufacturer</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="device_type" checked> Device Type</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="tags" checked> Tags</label></div>
                </div>
                <div class="col-md-6">
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="model" checked> Model</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="os" checked> Operating System</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="mdns_services" checked> mDNS Services</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="open_ports" checked> Open Ports</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="snmp_sysname"> SNMP sysName</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="snmp_sysdescr"> SNMP sysDescr</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="interface" checked> Interface</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="subnet" checked> Subnet</label></div>
                  <div class="checkbox"><label><input type="checkbox" class="col-toggle" data-col="via_ap" checked> Via AP (WiFi)</label></div>
                </div>
              </div>
              <p class="text-muted" style="margin-top:10px;font-size:90%;"><em>Note: Select, View, Flags (🏴), Connection (●), IP, Last Seen, and Edit columns are always visible.</em></p>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-default" id="btn_reset_columns">Reset to Defaults</button>
              <button type="button" class="btn btn-primary" data-dismiss="modal">Done</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Delete Confirmation Modal -->
      <div class="modal fade" id="deleteConfirmModal" tabindex="-1" role="dialog">
        <div class="modal-dialog modal-sm" role="document">
          <div class="modal-content">
            <div class="modal-header bg-danger">
              <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
              <h4 class="modal-title"><i class="fa fa-exclamation-triangle"></i> Confirm Delete</h4>
            </div>
            <div class="modal-body">
              <p><strong>Are you sure you want to delete this device?</strong></p>
              <p>Device: <strong><span id="delete_confirm_ip"></span></strong></p>
              <p class="text-muted">This will permanently remove the device from inventory, including all history and custom settings.</p>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
              <button type="button" class="btn btn-danger" id="btn_confirm_delete">Yes, Delete Device</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Bulk Tag Modal -->
      <div class="modal fade" id="bulkTagModal" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
              <h4 class="modal-title">Bulk Tag Devices</h4>
            </div>
            <div class="modal-body">
              <p>Add tags to <strong><span id="bulk_tag_count">0</span> selected device(s)</strong>:</p>
              <div class="form-group">
                <label>Tags (comma-separated)</label>
                <input type="text" class="form-control" id="bulk_tags_input" placeholder="e.g., production, monitored">
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
              <button type="button" class="btn btn-primary" id="btn_bulk_tag_save">Apply Tags</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Device Detail Modal (Read-Only) -->
      <div class="modal fade" id="deviceDetailModal" tabindex="-1" role="dialog">
        <div class="modal-dialog modal-lg" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
              <h4 class="modal-title">Device Details</h4>
            </div>
            <div class="modal-body" id="device_detail_body" style="max-height:500px;overflow-y:auto;">
              <!-- Content populated by JS -->
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
              <button type="button" class="btn btn-primary" id="btn_edit_from_detail">Edit Device</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Edit Device Modal -->
      <div class="modal fade" id="editDeviceModal" tabindex="-1" role="dialog">
        <div class="modal-dialog" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
              <h4 class="modal-title">Edit Device</h4>
            </div>
            <div class="modal-body">
              <form id="editDeviceForm">
                <input type="hidden" id="edit_ip">
                <input type="hidden" id="edit_mac">
                <div class="form-group">
                  <label>IP Address</label>
                  <input type="text" class="form-control" id="edit_ip_display" readonly>
                </div>
                <div class="form-group">
                  <label>MAC Address</label>
                  <input type="text" class="form-control" id="edit_mac_display" readonly>
                </div>
                <div class="form-group">
                  <label>Custom Hostname</label>
                  <input type="text" class="form-control" id="edit_hostname" placeholder="Leave empty to use discovered hostname">
                </div>
                <div class="form-group">
                  <label>Device Type</label>
                  <input type="text" class="form-control" id="edit_device_type" placeholder="e.g., printer, NAS, IoT, mobile">
                </div>
                <div class="form-group">
                  <label>Mfr (Manufacturer)</label>
                  <input type="text" class="form-control" id="edit_manufacturer" placeholder="Leave empty to use discovered manufacturer">
                  <span class="help-block">Overrides OUI vendor and SSDP/SNMP manufacturer</span>
                </div>
                <div class="form-group">
                  <label>Model</label>
                  <input type="text" class="form-control" id="edit_model" placeholder="Leave empty to use discovered model">
                </div>
                <div class="form-group">
                  <label>Operating System</label>
                  <input type="text" class="form-control" id="edit_os" placeholder="Leave empty to use detected OS">
                  <span class="help-block">OS name (e.g., Ubuntu Linux, Windows 10, macOS)</span>
                </div>
                <div class="form-group">
                  <label title="Physical and or Logical">Location <i class="fa fa-question-circle text-muted" title="Physical and or Logical"></i></label>
                  <input type="text" class="form-control" id="edit_location" placeholder="e.g., Building A / Rack 3 / VLAN 10, Conference Room">
                </div>
                <div class="form-group">
                  <label>Tags (comma-separated)</label>
                  <input type="text" class="form-control" id="edit_tags" placeholder="e.g., production, trusted, monitored">
                </div>
                <div class="form-group">
                  <label>Notes</label>
                  <textarea class="form-control" id="edit_notes" rows="3" placeholder="Additional notes"></textarea>
                </div>
              </form>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
              <button type="button" class="btn btn-warning" id="btn_delete_override">Clear Overrides</button>
              <button type="button" class="btn btn-danger" id="btn_delete_device">Delete Device</button>
              <button type="button" class="btn btn-primary" id="btn_save_device">Save</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="tab-pane" id="tab_events">
      <div style="display:flex;gap:8px;margin-bottom:10px;align-items:center;">
        <div class="input-group input-group-sm" style="width:300px;">
          <span class="input-group-addon"><i class="fa fa-search"></i></span>
          <input type="text" class="form-control" id="events_search" placeholder="Search events...">
          <span class="input-group-btn">
            <button class="btn btn-default" id="events_search_clear"><i class="fa fa-times"></i></button>
          </span>
        </div>
        <div class="btn-group btn-group-xs" role="group" aria-label="Event grouping">
          <button class="btn btn-default nd-filter-event-group" data-group="all" title="Show all events">All Events</button>
          <button class="btn btn-default nd-filter-event-group" data-group="latest" title="Show only most recent event per device">Latest Per Device</button>
        </div>
        <button class="btn btn-xs btn-default" id="btn_refresh_events" title="Refresh Now"><i class="fa fa-refresh"></i></button>
        <span class="text-muted" id="events_last_update" style="font-size:90%;"></span>
      </div>
      <div style="overflow-x:auto;">
        <table id="gridEvents" class="table table-condensed table-hover table-striped nd-sortable nd-resizable" data-editDialog="false">
          <thead>
            <tr>
              <th data-column-id="time" class="nd-sortable-col nd-resizable-col" data-sort-type="number" data-sort-dir="desc" style="width:180px;min-width:150px;">
                <div class="nd-th-content">Time <i class="fa fa-sort-desc"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="type" class="nd-sortable-col nd-resizable-col" style="width:120px;min-width:80px;">
                <div class="nd-th-content">Type <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="ip" class="nd-sortable-col nd-resizable-col" style="width:130px;min-width:100px;">
                <div class="nd-th-content">IP <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="mac" class="nd-sortable-col nd-resizable-col" style="width:150px;min-width:120px;">
                <div class="nd-th-content">MAC <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="hostname" class="nd-sortable-col nd-resizable-col" style="width:200px;min-width:100px;">
                <div class="nd-th-content">Hostname <i class="fa fa-sort"></i></div>
                <div class="nd-resize-handle"></div>
              </th>
              <th data-column-id="details" class="nd-resizable-col" style="width:300px;min-width:150px;">
                <div class="nd-th-content">Details</div>
                <div class="nd-resize-handle"></div>
              </th>
            </tr>
          </thead>
        </table>
      </div>
    </div>

    <div class="tab-pane" id="tab_settings">
      <div style="padding: 15px;">
        <p class="text-muted">Tune NetDiscover scanning and enrichment options, then click Save.</p>
        
        <div class="form-group">
        <label><input type="checkbox" id="general.enabled"> Enable NetDiscover</label>
      </div>
      <div class="form-group">
        <label>Scan interval (seconds)</label>
        <input type="text" class="form-control" id="general.interval">
        <span class="help-block">Default: 300</span>
      </div>
      
      <div class="form-group">
        <label><input type="checkbox" id="general.active_scan"> Active scan (ping sweep)</label>
      </div>
      <div class="form-group">
        <label><input type="checkbox" id="general.reverse_dns"> Reverse DNS enrichment (PTR)</label>
      </div>
      
      <div class="form-group">
        <label>Interfaces (optional)</label>
        <input type="text" class="form-control" id="general.interfaces">
        <span class="help-block">Default: _LAN_. Comma-separated; blank = all.</span>
      </div>
      
      <div class="form-group">
        <label>Max hosts per subnet (active scan)</label>
        <input type="text" class="form-control" id="general.max_hosts">
        <span class="help-block">Default: 4096</span>
      </div>
      <div class="form-group">
        <label>Ping rate limit (ms)</label>
        <input type="text" class="form-control" id="general.rate_limit_ms">
        <span class="help-block">Default: 3</span>
      </div>
      
      <hr>
      <h4>Discovery Protocols</h4>
      
      <div class="form-group">
        <label><input type="checkbox" id="general.ssdp_enable"> Enable SSDP/UPnP discovery</label>
      </div>
      <div class="form-group">
        <label><input type="checkbox" id="general.ssdp_fetch_xml"> Fetch UPnP description XML (friendlyName/manufacturer/model)</label>
      </div>
      <div class="form-group">
        <label>UPnP XML fetch rate limit (seconds per device)</label>
        <input type="text" class="form-control" id="general.ssdp_xml_rate_limit">
        <span class="help-block">Default: 10</span>
      </div>
      
      <div class="form-group">
        <label><input type="checkbox" id="general.mdns_enable"> Enable mDNS (Bonjour) discovery</label>
      </div>
      <div class="form-group">
        <label><input type="checkbox" id="general.llmnr_enable"> Enable LLMNR name discovery</label>
      </div>
      <div class="form-group">
        <label><input type="checkbox" id="general.nbns_enable"> Enable NetBIOS (NBNS) name discovery</label>
      </div>
      
      <hr>
      <h4>Optional Enrichment</h4>
      
      <div class="form-group">
        <label><input type="checkbox" id="general.tcp_probe_enable"> Enable TCP probes (fast port check)</label>
      </div>
      <div class="form-group">
        <label>Probe ports (comma-separated)</label>
        <input type="text" class="form-control" id="general.tcp_probe_ports">
        <span class="help-block">Default: 22,80,443,445,3389,9100</span>
      </div>
      <div class="form-group">
        <label>Probe timeout (ms)</label>
        <input type="text" class="form-control" id="general.tcp_probe_timeout_ms">
        <span class="help-block">Default: 250</span>
      </div>
      
      <div class="form-group">
        <label><input type="checkbox" id="general.snmp_enable"> Enable SNMP enrichment (sysName/sysDescr)</label>
      </div>
      <div class="form-group">
        <label>SNMP communities (comma-separated)</label>
        <input type="text" class="form-control" id="general.snmp_communities">
        <span class="help-block">Example: public,private. Uses snmpget if installed.</span>
      </div>
      <div class="form-group">
        <label>SNMP timeout (ms)</label>
        <input type="text" class="form-control" id="general.snmp_timeout_ms">
        <span class="help-block">Default: 400</span>
      </div>
      <div class="form-group">
        <label>SNMP rate limit per device (seconds)</label>
        <input type="text" class="form-control" id="general.snmp_rate_limit">
        <span class="help-block">Default: 3600</span>
      </div>
      
      
      <hr>
      <h4>MAC Vendor Database</h4>
      
      <div class="form-group">
        <label>MAC Vendor Database Source</label>
        <div class="btn-group" role="group">
          <button class="btn btn-success" id="btn_update_oui_wireshark" type="button">
            <i class="fa fa-download"></i> Wireshark Extended (Recommended)
          </button>
          <button class="btn btn-default" id="btn_update_oui_ieee" type="button">
            <i class="fa fa-download"></i> IEEE OUI (Standard)
          </button>
        </div>
        <span class="help-block">
          <strong>Wireshark Extended</strong> (recommended): ~35,000+ entries with model hints and detailed names.<br>
          <strong>IEEE OUI</strong> (standard): ~30,000 entries, manufacturer names only.<br>
          <em>Note: Sources are mutually exclusive - last one downloaded is used.</em>
        </span>
        <div id="oui_update_status" style="margin-top:8px;"></div>
      </div>
      </div>
    </div>
  </div>
</div>
<script src="{{ cache_safe('/ui/js/netdiscover/app.js') }}"></script>