
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Loader2, Search, Filter, ExternalLink, SlidersHorizontal, Plus, X, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"

const STANDARD_TAGS = ['app_name', 'version', 'business_name', 'application', 'payment'];

const SearchPage = () => {
    const [search, setSearch] = useState('');
    const [tags, setTags] = useState([{ key: '', value: '' }]);
    const [operator, setOperator] = useState('AND');
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(false);

    // Pagination State
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(10);

    const fetchDocuments = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (search) params.append('search', search);

            const validTags = tags.filter(t => t.key && t.value);
            if (validTags.length > 0) {
                const tagString = validTags.map(t => `${t.key}:${t.value}`).join(',');
                params.append('tags', tagString);
                params.append('operator', operator);
            }

            const response = await fetch(`http://localhost:3001/api/documents?${params.toString()}`);
            if (!response.ok) throw new Error('Failed to fetch documents');

            const data = await response.json();
            setDocuments(data);
            setCurrentPage(1); // Reset to first page on new search
        } catch (err) {
            toast.error(err.message || "Failed to load documents");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, []);

    const handleSearchSubmit = (e) => {
        e.preventDefault();
        fetchDocuments();
    };

    const handleTagChange = (index, field, value) => {
        const newTags = [...tags];
        newTags[index][field] = value;
        setTags(newTags);
    };

    const addTag = () => {
        setTags([...tags, { key: '', value: '' }]);
    };

    const removeTag = (index) => {
        const newTags = [...tags];
        newTags.splice(index, 1);
        setTags(newTags);
    };

    const handleDelete = async (id) => {
        if (!window.confirm("Are you sure you want to delete this document? This action cannot be undone.")) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:3001/api/documents/${id}`, {
                method: 'DELETE',
            });

            if (!response.ok) throw new Error('Failed to delete document');

            toast.success("Document deleted successfully");
            setDocuments(prev => prev.filter(doc => doc.id !== id));
        } catch (error) {
            toast.error(error.message || "Failed to delete document");
        }
    };

    // Pagination Logic
    const indexOfLastItem = currentPage * itemsPerPage;
    const indexOfFirstItem = indexOfLastItem - itemsPerPage;
    const currentDocuments = documents.slice(indexOfFirstItem, indexOfLastItem);
    const totalPages = Math.ceil(documents.length / itemsPerPage);

    const paginate = (pageNumber) => setCurrentPage(pageNumber);

    return (
        <div className="space-y-4">
            {/* Top Search Bar Area */}
            <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                <div className="flex flex-col gap-1">
                    <h1 className="text-2xl font-bold tracking-tight">Documents</h1>
                    <p className="text-sm text-muted-foreground">Manage and search your documentation knowledge base.</p>
                </div>
                <div className="w-full md:w-auto flex items-center gap-2">
                    <div className="relative w-full md:w-[300px]">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            className="pl-9 bg-background"
                            placeholder="Search titles..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && fetchDocuments()}
                        />
                    </div>
                    <Button onClick={fetchDocuments} size="sm">Search</Button>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-[280px_1fr]">
                {/* Filters Sidebar */}
                <div className="space-y-6">
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base">Filters</CardTitle>
                            <CardDescription className="text-xs">Refine your search results</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <form onSubmit={handleSearchSubmit} className="space-y-4">
                                <div className="space-y-2">
                                    <Label className="text-xs">Match Logic</Label>
                                    <div className="flex items-center gap-4 rounded-md border p-2 bg-muted/20">
                                        <label className="flex items-center gap-2 text-xs cursor-pointer">
                                            <input
                                                type="radio"
                                                name="operator"
                                                className="accent-primary"
                                                checked={operator === 'AND'}
                                                onChange={() => setOperator('AND')}
                                            />
                                            AND
                                        </label>
                                        <label className="flex items-center gap-2 text-xs cursor-pointer">
                                            <input
                                                type="radio"
                                                name="operator"
                                                className="accent-primary"
                                                checked={operator === 'OR'}
                                                onChange={() => setOperator('OR')}
                                            />
                                            OR
                                        </label>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <div className="flex items-center justify-between">
                                        <Label className="text-xs">Tags</Label>
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={addTag}
                                            className="h-6 px-2 text-[10px]"
                                        >
                                            <Plus className="h-3 w-3 mr-1" /> Add
                                        </Button>
                                    </div>
                                    <div className="space-y-2">
                                        {tags.map((tag, index) => (
                                            <div key={index} className="space-y-2 rounded-md border p-2 bg-muted/30">
                                                <div className="flex gap-2">
                                                    <Input
                                                        className="h-7 text-xs"
                                                        placeholder="Key"
                                                        list={`search-tags-${index}`}
                                                        value={tag.key}
                                                        onChange={(e) => handleTagChange(index, 'key', e.target.value)}
                                                    />
                                                    <datalist id={`search-tags-${index}`}>
                                                        {STANDARD_TAGS.map(t => <option key={t} value={t} />)}
                                                    </datalist>
                                                    {tags.length > 1 && (
                                                        <Button
                                                            type="button"
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                                                            onClick={() => removeTag(index)}
                                                        >
                                                            <X className="h-3 w-3" />
                                                        </Button>
                                                    )}
                                                </div>
                                                <Input
                                                    className="h-7 text-xs"
                                                    placeholder="Value"
                                                    value={tag.value}
                                                    onChange={(e) => handleTagChange(index, 'value', e.target.value)}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <Button type="submit" className="w-full" size="sm" disabled={loading}>
                                    {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : 'Apply Filters'}
                                </Button>
                            </form>
                        </CardContent>
                    </Card>
                </div>

                {/* Results Table */}
                <div className="space-y-4">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 py-4 px-6">
                            <div className="flex items-center gap-2">
                                <CardTitle className="text-base font-medium">Results</CardTitle>
                                <Badge variant="secondary" className="text-xs font-normal">{documents.length} Found</Badge>
                            </div>

                            {/* Items Per Page Dropdown */}
                            <div className="flex items-center space-x-2">
                                <Label className="text-xs text-muted-foreground">Rows:</Label>
                                <Select
                                    value={itemsPerPage.toString()}
                                    onValueChange={(value) => {
                                        setItemsPerPage(Number(value));
                                        setCurrentPage(1);
                                    }}
                                >
                                    <SelectTrigger className="h-8 w-[70px]">
                                        <SelectValue placeholder={itemsPerPage} />
                                    </SelectTrigger>
                                    <SelectContent side="top">
                                        {[10, 20, 50, 100].map((size) => (
                                            <SelectItem key={size} value={size.toString()}>
                                                {size}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="border-t">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-muted/50">
                                            <TableHead className="w-[45%]">Document</TableHead>
                                            <TableHead>Tags</TableHead>
                                            <TableHead className="text-right w-[120px]">Actions</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {loading ? (
                                            <TableRow>
                                                <TableCell colSpan={3} className="h-24 text-center">
                                                    <div className="flex items-center justify-center text-muted-foreground">
                                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                        Searching...
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        ) : currentDocuments.length > 0 ? (
                                            currentDocuments.map((doc) => (
                                                <TableRow key={doc.id} className="group">
                                                    <TableCell className="py-3">
                                                        <div className="flex flex-col gap-1">
                                                            <div className="flex items-center gap-2">
                                                                <span className="font-medium text-sm line-clamp-1">{doc.title}</span>
                                                                <Badge variant="outline" className="h-4 rounded-[4px] px-1 text-[9px] uppercase tracking-wider text-muted-foreground border-muted-foreground/30">
                                                                    {doc.type}
                                                                </Badge>
                                                            </div>
                                                            <span className="text-xs text-muted-foreground">{new Date(doc.createdAt).toLocaleDateString()}</span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="py-3">
                                                        <div className="flex flex-wrap gap-1">
                                                            {Object.entries(doc.tags || {}).map(([key, value]) => (
                                                                <Badge key={key} variant="secondary" className="px-1.5 py-0 text-[10px] font-normal border-transparent bg-secondary/50 hover:bg-secondary/80">
                                                                    <span className="font-semibold opacity-70 mr-1">{key}:</span>{value}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="text-right py-3">
                                                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                            <Button asChild variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-primary">
                                                                <a
                                                                    href={`http://localhost:3001${doc.localPath}${doc.type === 'git' ? '/index.html' : ''}`}
                                                                    target="_blank"
                                                                    rel="noopener noreferrer"
                                                                    title="Open"
                                                                >
                                                                    <ExternalLink className="h-4 w-4" />
                                                                </a>
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="h-8 w-8 text-muted-foreground hover:text-destructive"
                                                                onClick={() => handleDelete(doc.id)}
                                                                title="Delete"
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </div>
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        ) : (
                                            <TableRow>
                                                <TableCell colSpan={3} className="h-32 text-center text-muted-foreground text-sm">
                                                    No documents found matching your criteria.
                                                </TableCell>
                                            </TableRow>
                                        )}
                                    </TableBody>
                                </Table>
                            </div>

                            {/* Pagination Controls */}
                            {documents.length > 0 && (
                                <div className="flex items-center justify-between px-4 py-4 border-t">
                                    <div className="text-xs text-muted-foreground">
                                        Showing <strong>{indexOfFirstItem + 1}</strong> to <strong>{Math.min(indexOfLastItem, documents.length)}</strong> of <strong>{documents.length}</strong> results
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            className="h-8 w-8"
                                            onClick={() => paginate(currentPage - 1)}
                                            disabled={currentPage === 1}
                                        >
                                            <ChevronLeft className="h-4 w-4" />
                                        </Button>
                                        <div className="text-xs font-medium">
                                            Page {currentPage} of {totalPages}
                                        </div>
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            className="h-8 w-8"
                                            onClick={() => paginate(currentPage + 1)}
                                            disabled={currentPage === totalPages}
                                        >
                                            <ChevronRight className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            )}

                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default SearchPage;
