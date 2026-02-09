import React, { useContext } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Moon, Sun, FileText, Search, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ThemeContext } from '../App';

function Navbar() {
    const { theme, toggleTheme } = useContext(ThemeContext);
    const location = useLocation();

    const isActive = (path) => location.pathname === path;

    return (
        <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-14 items-center">
                <Link to="/" className="mr-6 flex items-center space-x-2">
                    <FileText className="h-6 w-6" />
                    <span className="hidden font-bold sm:inline-block">
                        DocManager
                    </span>
                </Link>
                <div className="mr-4 hidden md:flex">
                    <Link
                        to="/"
                        className={`mr-6 text-sm font-medium transition-colors hover:text-foreground/80 ${isActive('/') ? 'text-foreground' : 'text-foreground/60'}`}
                    >
                        Search
                    </Link>
                    <Link
                        to="/input"
                        className={`mr-6 text-sm font-medium transition-colors hover:text-foreground/80 ${isActive('/input') ? 'text-foreground' : 'text-foreground/60'}`}
                    >
                        Add Document
                    </Link>
                </div>
                <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
                    <div className="w-full flex-1 md:w-auto md:flex-none">
                        {/* Optional search input could go here */}
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={toggleTheme}
                        className="h-9 w-9 px-0"
                    >
                        {theme === 'light' ? (
                            <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                        ) : (
                            <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                        )}
                        <span className="sr-only">Toggle theme</span>
                    </Button>
                </div>
            </div>
        </nav>
    );
}

export default Navbar;
