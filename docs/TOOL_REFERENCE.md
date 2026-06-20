# Tool Reference

Tools are registered only when the corresponding product has at least one
entry in `config.yaml`. Every operational tool uses a configured `device_id`.
Run the product's list tool first.

## FortiGate (56)

### Discovery and Complete API

| Tool | Purpose |
|---|---|
| `fgt_list_devices` | List configured FortiGate devices |
| `fgt_api_request` | Call any documented FortiGate REST v2 endpoint |
| `fgt_api_batch` | Execute up to 50 ordered REST operations |
| `fgt_cmdb_request` | Call FortiGate configuration endpoints under `/api/v2/cmdb/` |
| `fgt_cmdb_batch` | Execute ordered configuration requests |
| `fgt_monitor_request` | Call FortiGate monitor endpoints under `/api/v2/monitor/` |
| `fgt_monitor_batch` | Execute ordered monitor requests |
| `fgt_log_request` | Call FortiGate log endpoints under `/api/v2/log/` |
| `fgt_log_batch` | Execute ordered log requests |
| `fgt_service_request` | Call FortiGate service endpoints under `/api/v2/service/` |
| `fgt_service_batch` | Execute ordered service requests |
| `fgt_get_system_status` | Firmware, serial number, and uptime |
| `fgt_get_system_resources` | CPU and memory usage |
| `fgt_get_interfaces` | Network interfaces |
| `fgt_backup_config` | Retrieve a full configuration backup |
| `fgt_execute_cli` | Execute CLI commands |
| `fgt_get_ha_status` | HA cluster status |

### Firewall Policy and Objects

| Tool | Purpose |
|---|---|
| `fgt_get_firewall_policies` | List or retrieve firewall policies |
| `fgt_create_firewall_policy` | Create a firewall policy |
| `fgt_update_firewall_policy` | Update a firewall policy |
| `fgt_delete_firewall_policy` | Delete a firewall policy |
| `fgt_move_firewall_policy` | Reorder a firewall policy |
| `fgt_get_address_objects` | List address objects |
| `fgt_create_address_object` | Create an address object |
| `fgt_update_address_object` | Update an address object |
| `fgt_delete_address_object` | Delete an address object |
| `fgt_get_address_groups` | List address groups |
| `fgt_create_address_group` | Create an address group |
| `fgt_update_address_group` | Update an address group |
| `fgt_delete_address_group` | Delete an address group |
| `fgt_get_service_objects` | List service objects |
| `fgt_create_service_object` | Create a service object |
| `fgt_update_service_object` | Update a service object |
| `fgt_delete_service_object` | Delete a service object |
| `fgt_get_service_groups` | List service groups |
| `fgt_create_service_group` | Create a service group |
| `fgt_update_service_group` | Update a service group |
| `fgt_delete_service_group` | Delete a service group |

### Routing and VPN

| Tool | Purpose |
|---|---|
| `fgt_get_static_routes` | List configured static routes |
| `fgt_create_static_route` | Create a static route |
| `fgt_update_static_route` | Update a static route |
| `fgt_delete_static_route` | Delete a static route |
| `fgt_get_routing_table` | Active routing table |
| `fgt_get_bgp_neighbors` | BGP neighbor state |
| `fgt_get_ipsec_tunnels` | Active IPsec tunnel state |
| `fgt_get_ipsec_phase1_config` | IPsec phase 1 configuration |
| `fgt_create_ipsec_phase1` | Create an IPsec phase 1 interface |
| `fgt_update_ipsec_phase1` | Update an IPsec phase 1 interface |
| `fgt_delete_ipsec_phase1` | Delete an IPsec phase 1 interface |
| `fgt_get_ssl_vpn_settings` | SSL-VPN settings |
| `fgt_get_ssl_vpn_sessions` | Active SSL-VPN sessions |

### Monitoring and Logs

| Tool | Purpose |
|---|---|
| `fgt_get_active_sessions` | Active firewall sessions |
| `fgt_get_session_stats` | Session table statistics |
| `fgt_get_fortiview_top_sources` | Top FortiView source statistics |
| `fgt_get_threat_feeds` | Configured threat feeds |
| `fgt_get_logs` | Retrieve FortiGate disk logs |

Use a typed tool when one matches the workflow. Use `fgt_cmdb_request`,
`fgt_monitor_request`, `fgt_log_request`, or `fgt_service_request` when you
want explicit domain scoping. Use `fgt_api_request` when the request needs to
cross domains or when the domain is already embedded in the full FortiOS path.

Write-capable tools include CLI execution, all create/update/delete/reorder
operations, and generic API calls using `post`, `put`, or `delete`. Read
current state and prepare rollback data first.

## FortiManager (31)

| Tool | Purpose |
|---|---|
| `fmg_list_devices` | List configured FortiManager instances |
| `fmg_get_system_status` | Version, serial number, and uptime |
| `fmg_get_adoms` | List ADOMs |
| `fmg_get_managed_devices` | List managed devices in an ADOM |
| `fmg_get_device_detail` | Retrieve one managed device |
| `fmg_add_device` | Add/import a FortiGate |
| `fmg_delete_device` | Remove a managed device |
| `fmg_get_unregistered_devices` | List devices awaiting registration |
| `fmg_set_device_metadata` | Set provisioning metadata |
| `fmg_get_policy_packages` | List policy packages |
| `fmg_create_policy_package` | Create a policy package |
| `fmg_install_policy_package` | Install a package to target devices |
| `fmg_install_device_config` | Install device-level configuration |
| `fmg_get_firewall_policies` | List policies in a package |
| `fmg_create_firewall_policy` | Create a package policy |
| `fmg_update_firewall_policy` | Update a package policy |
| `fmg_delete_firewall_policy` | Delete a package policy |
| `fmg_get_address_objects` | List ADOM address objects |
| `fmg_create_address_object` | Create an ADOM address object |
| `fmg_update_address_object` | Update an ADOM address object |
| `fmg_delete_address_object` | Delete an ADOM address object |
| `fmg_get_address_groups` | List ADOM address groups |
| `fmg_create_address_group` | Create an ADOM address group |
| `fmg_get_service_objects` | List ADOM service objects |
| `fmg_create_service_object` | Create an ADOM service object |
| `fmg_get_scripts` | List CLI scripts |
| `fmg_create_script` | Create a CLI script |
| `fmg_run_script` | Execute a script on managed devices |
| `fmg_get_task_status` | Retrieve a task |
| `fmg_get_tasks` | List recent tasks |
| `fmg_wait_for_task` | Poll a task until completion or timeout |

Install and script operations are asynchronous. Preserve the returned task ID
and poll it to a terminal state.

## FortiAnalyzer (29)

### Discovery and Complete API

| Tool | Purpose |
|---|---|
| `faz_list_devices` | List configured FortiAnalyzer instances |
| `faz_get_system_status` | Version, serial number, and disk status |
| `faz_get_adoms` | List ADOMs |
| `faz_get_registered_devices` | List log-sending devices |
| `faz_get_device_groups` | List device groups |
| `faz_api_request` | Call any documented v8 JSON-RPC method and URL |
| `faz_api_batch` | Execute up to 50 ordered v8 operations |

### Logs

| Tool | Purpose |
|---|---|
| `faz_get_log_fields` | Discover fields for a device and log type |
| `faz_query_logs` | Start a v8 log-search task |
| `faz_search_logs` | Alias for starting a log-search task |
| `faz_get_log_search_results` | Poll and page task results |
| `faz_get_log_search_count` | Retrieve the task result count |
| `faz_delete_log_search` | Delete a completed log-search task |

### Reports

| Tool | Purpose |
|---|---|
| `faz_get_reports` | List generated reports by state |
| `faz_get_report_templates` | List report templates |
| `faz_run_report` | Start a report task |
| `faz_get_report_status` | Poll report task status |
| `faz_download_report` | Retrieve completed report output |

### Incidents, Alerts, and Analytics

| Tool | Purpose |
|---|---|
| `faz_get_incidents` | List security incidents |
| `faz_get_events` | List security alerts |
| `faz_get_event_handlers` | Retrieve handler filters for alert IDs |
| `faz_get_traffic_summary` | Retrieve device log statistics |
| `faz_get_threat_summary` | Start the top-threats FortiView task |
| `faz_start_fortiview` | Start any documented FortiView task |
| `faz_get_fortiview_results` | Poll FortiView results |
| `faz_delete_fortiview` | Delete a completed FortiView task |
| `faz_get_top_sources` | Start the top-sources task |
| `faz_get_top_threats` | Start the top-threats task |
| `faz_get_top_applications` | Start the top-applications task |

See the [FortiAnalyzer runbook](FORTIANALYZER_RUNBOOK.md) for arguments and
task sequences. The generic API tools can perform destructive operations; the
method name alone does not determine risk because `exec` and `execute` may
trigger appliance actions.

## MCP Resource

`fortinet://health` returns server status and the configured inventory without
including passwords, API keys, or sessions. It is an MCP resource, not an HTTP
`/health` route.
