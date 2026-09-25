import {
  Activity, EyeOff, FileText, FlaskConical, FolderKanban, Inbox, LayoutDashboard, Pill, Settings, Stethoscope, UserCog, Users,
  type LucideIcon,
} from "lucide-react";
import type { NavIcon } from "@/lib/navigation";

export const NAV_ICONS: Record<NavIcon, LucideIcon> = {
  "layout-dashboard": LayoutDashboard, users: Users, inbox: Inbox, "file-text": FileText, "eye-off": EyeOff,
  "folder-kanban": FolderKanban, "flask-conical": FlaskConical, pill: Pill, stethoscope: Stethoscope,
  "user-cog": UserCog, settings: Settings, activity: Activity,
};
