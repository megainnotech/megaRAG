
import React from 'react';
import { NavLink } from 'react-router-dom';
import { FileText, Upload, LayoutDashboard, Settings, Search } from 'lucide-react';
import { cn } from '@/lib/utils';

const Sidebar = () => {
    const navItems = [
        { name: 'Documents', path: '/', icon: FileText },
        { name: 'Add Document', path: '/input', icon: Upload },
        { name: 'Retrieve', path: '/retrieve', icon: Search },
    ];

    return (
        <div className="hidden border-r bg-muted/40 md:block w-[220px] lg:w-[280px] h-screen sticky top-0">
            <div className="flex h-full max-h-screen flex-col gap-2">
                <div className="flex h-14 items-center border-b px-4 lg:h-[60px] lg:px-6">
                    <div className="flex items-center gap-2 font-semibold">
                        <div className="h-6 w-6 bg-primary rounded-md flex items-center justify-center">
                            <LayoutDashboard className="h-4 w-4 text-primary-foreground" />
                        </div>
                        <span className="">DocManager</span>
                    </div>
                </div>
                <div className="flex-1">
                    <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) =>
                                    cn(
                                        "flex items-center gap-3 rounded-lg px-3 py-2 transition-all hover:text-primary",
                                        isActive
                                            ? "bg-muted text-primary"
                                            : "text-muted-foreground"
                                    )
                                }
                            >
                                <item.icon className="h-4 w-4" />
                                {item.name}
                            </NavLink>
                        ))}
                    </nav>
                </div>
                {/* Optional footer area */}
                <div className="mt-auto p-4">
                    {/* Add settings or other footer links later */}
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
