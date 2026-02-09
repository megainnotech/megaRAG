
import React, { useContext } from 'react';
import { Moon, Sun, Menu, Search as SearchIcon, FileText, Upload, LayoutDashboard } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { ThemeContext } from '@/App';
import { cn } from '@/lib/utils';
import Sidebar from './Sidebar';

const MobileNav = () => {
    const navItems = [
        { name: 'Documents', path: '/', icon: FileText },
        { name: 'Add Document', path: '/input', icon: Upload },
    ];

    return (
        <div className="flex flex-col gap-4 py-4">
            <div className="flex items-center gap-2 font-semibold px-2">
                <div className="h-6 w-6 bg-primary rounded-md flex items-center justify-center">
                    <LayoutDashboard className="h-4 w-4 text-primary-foreground" />
                </div>
                <span>DocManager</span>
            </div>
            <nav className="grid gap-2 text-sm font-medium">
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
    );
};

const AppLayout = ({ children }) => {
    const { theme, toggleTheme } = useContext(ThemeContext);

    return (
        <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
            <Sidebar />
            <div className="flex flex-col">
                <header className="flex h-14 items-center gap-4 border-b bg-muted/40 px-4 lg:h-[60px] lg:px-6 sticky top-0 z-10 backdrop-blur bg-background/95 justify-between md:justify-end">
                    <Sheet>
                        <SheetTrigger asChild>
                            <Button
                                variant="outline"
                                size="icon"
                                className="shrink-0 md:hidden"
                            >
                                <Menu className="h-5 w-5" />
                                <span className="sr-only">Toggle navigation menu</span>
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="left" className="flex flex-col">
                            <MobileNav />
                        </SheetContent>
                    </Sheet>

                    <div className="w-full flex-1 md:hidden">
                        {/* Spacer or Mobile Title */}
                    </div>

                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={toggleTheme}
                        className="h-9 w-9 px-0 rounded-full"
                    >
                        <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                        <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                        <span className="sr-only">Toggle theme</span>
                    </Button>
                </header>
                <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6 bg-background">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default AppLayout;
