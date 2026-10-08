/*
 * NetDiscover Widget - Device discovery summary and recent events
 */

export default class NetDiscoverWidget extends BaseTableWidget {
    constructor() {
        super();
    }

    getGridOptions() {
        return {
            sizeToContent: 500
        };
    }

    getMarkup() {
        let $container = $('<div class="netdiscover-widget-container"></div>');
        
        // Header with link
        let $header = $(`
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div style="font-weight:bold;">${this.translations.title || 'Device Discovery Summary'}</div>
                <a href="/ui/netdiscover" class="btn btn-xs btn-default" title="View Full Inventory">
                    <i class="fa fa-external-link"></i>
                </a>
            </div>
        `);
        $container.append($header);
        
        // Stats badges
        let $stats = $(`
            <div class="netdiscover-widget-stats" style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
                <div style="padding:6px 10px;background:#5bc0de;color:#fff;border-radius:3px;">
                    <b>Total</b>: <span class="nd-total">-</span>
                </div>
                <div style="padding:6px 10px;background:#5cb85c;color:#fff;border-radius:3px;">
                    <b>Up (10m)</b>: <span class="nd-up">-</span>
                </div>
                <div style="padding:6px 10px;background:#f0ad4e;color:#fff;border-radius:3px;">
                    <b>New (24h)</b>: <span class="nd-new">-</span>
                </div>
                <div style="padding:6px 10px;background:#428bca;color:#fff;border-radius:3px;">
                    <b>Changed (24h)</b>: <span class="nd-chg">-</span>
                </div>
                <div style="padding:6px 10px;background:#d9534f;color:#fff;border-radius:3px;">
                    <b>Gone (24h)</b>: <span class="nd-gone">-</span>
                </div>
            </div>
        `);
        $container.append($stats);
        
        // Recent events table
        let $table = this.createTable('netdiscoverEventsTable', {
            headerPosition: 'top',
            headers: ['Time', 'Type', 'IP', 'MAC/Host']
        });
        $container.append($table);
        
        return $container;
    }

    async onWidgetTick() {
        const data = await this.ajaxCall('/api/netdiscover/dashboard/summary');
        
        if (!data) {
            this.displayError('Error loading data');
            return;
        }
        
        // Update stats
        $('.nd-total').text(data.total || '0');
        $('.nd-up').text(data.up_10m || '0');
        $('.nd-new').text(data.new_24h || '0');
        $('.nd-chg').text(data.changed_24h || '0');
        $('.nd-gone').text(data.gone_24h || '0');
        
        // Update events table with colored indicators (deduplicated)
        const events = data.recent_events || [];
        const rows = [];
        
        if (events.length === 0) {
            rows.push(['', '', 'No recent events', '']);
        } else {
            // Deduplicate: Keep only most recent event per device
            const seenIPs = new Set();
            const uniqueEvents = [];
            
            events.forEach((e) => {
                const ip = e.ip || '';
                if (!seenIPs.has(ip)) {
                    seenIPs.add(ip);
                    uniqueEvents.push(e);
                }
            });
            
            uniqueEvents.slice(0, 10).forEach((e) => {
                const ts = e.time ? new Date(parseInt(e.time, 10) * 1000).toLocaleTimeString() : '';
                const type = e.type || '';
                const ip = e.ip || '';
                const who = (e.mac || '') + (e.hostname ? (' / ' + e.hostname) : '');
                
                // Create colored indicator for type - v1.5.0 colors
                let color = '#999'; // default gray
                if (type === 'new') color = '#f0ad4e'; // orange
                else if (type === 'up') color = '#5cb85c'; // green
                else if (type === 'back') color = '#5bc0de'; // cyan
                else if (type === 'changed') color = '#428bca'; // light blue
                else if (type === 'offline') color = '#f0ad4e'; // yellow/orange
                else if (type === 'gone') color = '#d9534f'; // red
                
                const typeWithDot = '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background-color:' + color + ';margin-right:6px;"></span>' + type;
                
                rows.push([ts, typeWithDot, ip, who]);
            });
        }
        
        this.updateTable('netdiscoverEventsTable', rows);
    }

    displayError(message) {
        const $error = $(`
            <div class="error-message">
                <a href="/ui/netdiscover" target="_blank">${message}</a>
            </div>
        `);
        $('#netdiscoverEventsTable').empty().append($error);
    }
}
