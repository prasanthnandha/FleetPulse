"""
FleetPulse — Ticket Drafting Tool
===================================
Agent tool that drafts structured remediation/replacement tickets.
"""

from datetime import datetime


class TicketTool:
    """Drafts remediation tickets from prediction and repair info."""

    def execute(self, arguments: dict) -> dict:
        """
        Draft a remediation ticket.

        Args:
            arguments: Tool call arguments with ticket details.

        Returns:
            Structured ticket dict.
        """
        device_id = arguments.get("device_id", "UNKNOWN")
        device_model = arguments.get("device_model", "Unknown Model")
        issue_summary = arguments.get("issue_summary", "Device health issue detected")
        component = arguments.get("predicted_failure_component", "unknown")
        rul_days = arguments.get("remaining_useful_life_days")
        part_number = arguments.get("part_number")
        supplier = arguments.get("supplier")
        repair_time = arguments.get("estimated_repair_time_hours")
        cost = arguments.get("cost_usd")
        priority = arguments.get("priority", self._auto_priority(rul_days))
        fleet = arguments.get("assigned_fleet", "")
        notes = arguments.get("additional_notes", "")

        now = datetime.utcnow()
        ticket_id = f"FP-{now.strftime('%Y%m%d')}-{device_id[-4:]}"

        ticket = {
            "ticket_id": ticket_id,
            "created_at": now.isoformat() + "Z",
            "status": "Draft",
            "priority": priority,
            "type": "Preventive Maintenance" if rul_days and rul_days > 7 else "Urgent Repair",
            "device": {
                "device_id": device_id,
                "device_model": device_model,
                "fleet": fleet,
                "failing_component": component,
            },
            "prediction": {
                "issue_summary": issue_summary,
                "remaining_useful_life_days": rul_days,
                "urgency": self._urgency_label(rul_days),
            },
            "repair_details": {
                "part_number": part_number,
                "supplier": supplier,
                "estimated_repair_time_hours": repair_time,
                "estimated_cost_usd": cost,
            },
            "actions": [
                f"1. Order replacement {component.replace('_', ' ')} (Part: {part_number or 'TBD'})"
                if part_number
                else f"1. Identify replacement {component.replace('_', ' ')} part",
                f"2. Schedule {repair_time or '?'}-hour repair window with device owner",
                "3. Back up device data before repair",
                f"4. Perform {component.replace('_', ' ')} replacement following service manual procedure",
                "5. Run post-repair diagnostics and MDM compliance check",
                "6. Return device to user and close ticket",
            ],
            "estimated_downtime_hours": repair_time or 2.0,
            "estimated_cost_usd": cost,
            "additional_notes": notes,
            "formatted_summary": self._format_ticket_summary(
                ticket_id,
                priority,
                device_id,
                device_model,
                fleet,
                issue_summary,
                component,
                rul_days,
                part_number,
                supplier,
                repair_time,
                cost,
                notes,
            ),
        }

        return ticket

    @staticmethod
    def _auto_priority(rul_days: float | None) -> str:
        """Assign priority based on remaining useful life."""
        if rul_days is None:
            return "P3"
        if rul_days <= 7:
            return "P1"
        elif rul_days <= 14:
            return "P2"
        elif rul_days <= 30:
            return "P3"
        return "P4"

    @staticmethod
    def _urgency_label(rul_days: float | None) -> str:
        if rul_days is None:
            return "Unknown"
        if rul_days <= 7:
            return "🔴 Critical — failure expected within 1 week"
        elif rul_days <= 14:
            return "🟠 High — failure expected within 2 weeks"
        elif rul_days <= 30:
            return "🟡 Medium — failure expected within 1 month"
        return "🟢 Low — no imminent failure predicted"

    @staticmethod
    def _format_ticket_summary(
        ticket_id,
        priority,
        device_id,
        device_model,
        fleet,
        issue_summary,
        component,
        rul_days,
        part_number,
        supplier,
        repair_time,
        cost,
        notes,
    ) -> str:
        lines = [
            "═══════════════════════════════════════════════",
            f"  REMEDIATION TICKET — {ticket_id}",
            "═══════════════════════════════════════════════",
            "",
            f"  Priority:    {priority}",
            "  Status:      Draft",
            f"  Created:     {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "  ── Device ──────────────────────────────────",
            f"  ID:          {device_id}",
            f"  Model:       {device_model}",
            f"  Fleet:       {fleet or 'N/A'}",
            f"  Component:   {component.replace('_', ' ').title()}",
            "",
            "  ── Issue ───────────────────────────────────",
            f"  Summary:     {issue_summary}",
            f"  RUL:         {rul_days or 'N/A'} days",
            "",
            "  ── Repair Info ─────────────────────────────",
            f"  Part Number: {part_number or 'TBD'}",
            f"  Supplier:    {supplier or 'TBD'}",
            f"  Repair Time: {repair_time or 'TBD'} hours",
            f"  Est. Cost:   ${cost:.2f}" if cost else "  Est. Cost:   TBD",
            "",
        ]
        if notes:
            lines.extend(
                [
                    "  ── Notes ───────────────────────────────────",
                    f"  {notes}",
                    "",
                ]
            )
        lines.append("═══════════════════════════════════════════════")
        return "\n".join(lines)
