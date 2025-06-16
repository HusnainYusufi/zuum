at_pickup_output_format = """
{
  "schema": {
    "type": "object",
    "properties": {
      "Dock_number": {
        "type": "string",
        "nullable": true,
        "description": "The dock number assigned to the driver"
      },
      "Unloading_duration_estimate": {
        "type": "string",
        "nullable": true,
        "description": "Estimated time to complete unloading as quoted to the driver"
      },
      "Needs_lumper_code": {
        "type": "boolean",
        "description": "Whether the driver is requesting a lumper code"
      },
      "Checked_in": {
        "type": "boolean",
        "description": "Whether the driver has checked in at the receiver"
      },
      "Lumper_payment_method": {
        "type": "string",
        "nullable": true,
        "description": "Accepted payment method for lumper (e.g., Comchek, EFS, T-Check)"
      },
      "OSD_reported": {
        "type": "boolean",
        "description": "Whether any overages, shortages, or damages were reported by the warehouse"
      },
      "Lumper_fee_amount": {
        "type": "string",
        "nullable": true,
        "description": "Amount requested for lumper (e.g., '$95')"
      },
      "OSD_details": {
        "type": "string",
        "nullable": true,
        "description": "Details about any overages, shortages, or damages"
      },
      "Unloading_started": {
        "type": "boolean",
        "description": "Whether unloading has started"
      }
    },
    "required": [
      "Checked_in",
      "Unloading_started",
      "Needs_lumper_code",
      "OSD_reported"
    ]
  },
  "example_output": {
    "Dock_number": "Example Dock number",
    "Unloading_duration_estimate": "Example Unloading duration estimate",
    "Needs_lumper_code": true,
    "Checked_in": true,
    "Lumper_payment_method": "Example Lumper payment method",
    "OSD_reported": true,
    "Lumper_fee_amount": "Example Lumper fee amount",
    "OSD_details": "2024-01-15 14:30",
    "Unloading_started": true
  }
}
"""