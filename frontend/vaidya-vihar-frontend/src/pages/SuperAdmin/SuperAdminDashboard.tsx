import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

type Brand = {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  is_active: boolean;
};

type CompanyCEO = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
};

type Company = {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  is_active: boolean;
  users_count: number;
  brands_count: number;
  branches_count: number;
  brands: Brand[];
  ceo?: CompanyCEO | null;
};

type UserSummary = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_super_admin?: boolean;
};

type DashboardSummary = {
  total_companies: number;
  active_companies: number;
  total_users: number;
  total_branches: number;
  total_brands: number;
};

const API_BASE = 'http://127.0.0.1:8000';

const authHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    Authorization: `Bearer ${token || ''}`,
  };
};

const emptyCompanyForm = {
  name: '',
  slug: '',
  description: '',
  is_active: true,
};

export default function SuperAdminDashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<DashboardSummary>({
    total_companies: 0,
    active_companies: 0,
    total_users: 0,
    total_branches: 0,
    total_brands: 0,
  });
  const [companies, setCompanies] = useState<Company[]>([]);
  const [systemUsers, setSystemUsers] = useState<UserSummary[]>([]);
  const [companyForm, setCompanyForm] = useState(emptyCompanyForm);
  const [editingCompanyId, setEditingCompanyId] = useState<number | null>(null);
  const [brandDrafts, setBrandDrafts] = useState<Record<number, string>>({});
  const [submittingCompany, setSubmittingCompany] = useState(false);
  const [submittingBrand, setSubmittingBrand] = useState<Record<number, boolean>>({});
  const [assigningCeo, setAssigningCeo] = useState<Record<number, boolean>>({});

  const canAccessSuperAdmin = useMemo(() => {
    const role = (user?.role || '').trim().toLowerCase();
    return Boolean(user?.is_super_admin || role === 'super_admin' || role === 'super_ceo');
  }, [user]);

  useEffect(() => {
    if (!user) {
      navigate('/');
      return;
    }

    if (!canAccessSuperAdmin) {
      navigate('/branch/dashboard');
      return;
    }

    loadDashboard();
  }, [canAccessSuperAdmin, navigate, user]);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [dashboardRes, usersRes] = await Promise.all([
        axios.get(`${API_BASE}/api/super-admin/dashboard`, { headers: authHeaders() }),
        axios.get(`${API_BASE}/api/super-admin/users`, { headers: authHeaders() }),
      ]);

      setSummary(dashboardRes.data.summary || {});
      setCompanies(dashboardRes.data.companies || []);
      setSystemUsers(usersRes.data.users || []);
    } catch (error: any) {
      console.error('Failed to load super-admin dashboard', error);
      toast.error(error?.response?.data?.detail || 'Unable to load super-admin dashboard');
    } finally {
      setLoading(false);
    }
  };

  const resetCompanyForm = () => {
    setCompanyForm(emptyCompanyForm);
    setEditingCompanyId(null);
  };

  const handleCompanySubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const payload = {
      name: companyForm.name.trim(),
      slug: companyForm.slug.trim() || undefined,
      description: companyForm.description.trim() || undefined,
      is_active: companyForm.is_active,
    };

    if (!payload.name) {
      toast.error('Company name is required');
      return;
    }

    try {
      setSubmittingCompany(true);
      if (editingCompanyId) {
        await axios.put(`${API_BASE}/api/super-admin/companies/${editingCompanyId}`, payload, {
          headers: authHeaders(),
        });
        toast.success('Company updated');
      } else {
        await axios.post(`${API_BASE}/api/super-admin/companies`, payload, {
          headers: authHeaders(),
        });
        toast.success('Company created');
      }
      resetCompanyForm();
      await loadDashboard();
    } catch (error: any) {
      console.error('Failed to save company', error);
      toast.error(error?.response?.data?.detail || 'Unable to save company');
    } finally {
      setSubmittingCompany(false);
    }
  };

  const handleEditCompany = (company: Company) => {
    setEditingCompanyId(company.id);
    setCompanyForm({
      name: company.name,
      slug: company.slug,
      description: company.description || '',
      is_active: company.is_active,
    });
  };

  const handleDeleteCompany = async (companyId: number) => {
    const confirmed = window.confirm('Archive this company? This hides it from active listings.');
    if (!confirmed) return;

    try {
      await axios.delete(`${API_BASE}/api/super-admin/companies/${companyId}`, {
        headers: authHeaders(),
      });
      toast.success('Company archived');
      await loadDashboard();
    } catch (error: any) {
      console.error('Failed to archive company', error);
      toast.error(error?.response?.data?.detail || 'Unable to archive company');
    }
  };

  const handleCreateBrand = async (companyId: number) => {
    const brandName = (brandDrafts[companyId] || '').trim();
    if (!brandName) {
      toast.error('Brand name is required');
      return;
    }

    try {
      setSubmittingBrand((prev) => ({ ...prev, [companyId]: true }));
      await axios.post(
        `${API_BASE}/api/super-admin/companies/${companyId}/brands`,
        {
          name: brandName,
          is_active: true,
        },
        { headers: authHeaders() }
      );
      toast.success('Brand added');
      setBrandDrafts((prev) => ({ ...prev, [companyId]: '' }));
      await loadDashboard();
    } catch (error: any) {
      console.error('Failed to create brand', error);
      toast.error(error?.response?.data?.detail || 'Unable to create brand');
    } finally {
      setSubmittingBrand((prev) => ({ ...prev, [companyId]: false }));
    }
  };

  const handleAssignCeo = async (companyId: number) => {
    const select = document.getElementById(`ceo-select-${companyId}`) as HTMLSelectElement | null;
    const selectedUserId = Number(select?.value || '0');
    if (!selectedUserId) {
      toast.error('Please select a user to assign as CEO');
      return;
    }

    try {
      setAssigningCeo((prev) => ({ ...prev, [companyId]: true }));
      await axios.post(
        `${API_BASE}/api/super-admin/companies/${companyId}/ceo`,
        { user_id: selectedUserId },
        { headers: authHeaders() }
      );
      toast.success('CEO assigned');
      await loadDashboard();
    } catch (error: any) {
      console.error('Failed to assign CEO', error);
      toast.error(error?.response?.data?.detail || 'Unable to assign CEO');
    } finally {
      setAssigningCeo((prev) => ({ ...prev, [companyId]: false }));
    }
  };

  const handleRemoveCeo = async (companyId: number) => {
    try {
      await axios.delete(`${API_BASE}/api/super-admin/companies/${companyId}/ceo`, {
        headers: authHeaders(),
      });
      toast.success('CEO removed');
      await loadDashboard();
    } catch (error: any) {
      console.error('Failed to remove CEO', error);
      toast.error(error?.response?.data?.detail || 'Unable to remove CEO');
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-300">System access</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight">Super CEO Dashboard</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-white/10 px-3 py-1 text-sm font-medium text-slate-100">
              {user?.username || 'super-admin'}
            </div>
            <button
              type="button"
              onClick={() => {
                logout();
                navigate('/');
              }}
              className="rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-8 px-6 py-8">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {[
            { label: 'Total Companies', value: summary.total_companies },
            { label: 'Active Companies', value: summary.active_companies },
            { label: 'Users', value: summary.total_users },
            { label: 'Branches', value: summary.total_branches },
            { label: 'Brands', value: summary.total_brands },
          ].map((stat) => (
            <div key={stat.label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-500">{stat.label}</p>
              <p className="mt-4 text-3xl font-black text-slate-900">{stat.value}</p>
            </div>
          ))}
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Company management</p>
              <h2 className="mt-2 text-2xl font-black text-slate-900">
                {editingCompanyId ? 'Edit company' : 'Create company'}
              </h2>
            </div>
            {editingCompanyId && (
              <button
                type="button"
                onClick={resetCompanyForm}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
            )}
          </div>

          <form onSubmit={handleCompanySubmit} className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-slate-700">
              Company name
              <input
                value={companyForm.name}
                onChange={(event) => setCompanyForm((prev) => ({ ...prev, name: event.target.value }))}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2.5 outline-none transition focus:border-indigo-500 focus:bg-white"
                placeholder="Acme Labs"
              />
            </label>

            <label className="block text-sm font-medium text-slate-700">
              Slug
              <input
                value={companyForm.slug}
                onChange={(event) => setCompanyForm((prev) => ({ ...prev, slug: event.target.value }))}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2.5 outline-none transition focus:border-indigo-500 focus:bg-white"
                placeholder="acme-labs"
              />
            </label>

            <label className="block text-sm font-medium text-slate-700 md:col-span-2">
              Description
              <textarea
                value={companyForm.description}
                onChange={(event) => setCompanyForm((prev) => ({ ...prev, description: event.target.value }))}
                className="mt-2 min-h-[100px] w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2.5 outline-none transition focus:border-indigo-500 focus:bg-white"
                placeholder="Healthcare group management platform"
              />
            </label>

            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input
                type="checkbox"
                checked={companyForm.is_active}
                onChange={(event) => setCompanyForm((prev) => ({ ...prev, is_active: event.target.checked }))}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              Active company
            </label>

            <div className="flex items-end justify-end md:col-span-2">
              <button
                type="submit"
                disabled={submittingCompany}
                className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submittingCompany ? 'Saving...' : editingCompanyId ? 'Update company' : 'Create company'}
              </button>
            </div>
          </form>
        </section>

        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-black text-slate-900">Companies</h2>
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-indigo-700">
              {companies.length} records
            </span>
          </div>

          {loading ? (
            <div className="rounded-3xl border border-slate-200 bg-white p-12 text-center text-slate-500 shadow-sm">
              Loading dashboard...
            </div>
          ) : companies.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500 shadow-sm">
              No companies found. Create the first company to begin.
            </div>
          ) : (
            <div className="space-y-5">
              {companies.map((company) => (
                <article key={company.id} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-col gap-4 border-b border-slate-200 pb-4 xl:flex-row xl:items-start xl:justify-between">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="text-2xl font-black text-slate-900">{company.name}</h3>
                        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${company.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'}`}>
                          {company.is_active ? 'Active' : 'Archived'}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-slate-500">Slug: {company.slug}</p>
                      {company.description && <p className="mt-2 max-w-3xl text-sm text-slate-600">{company.description}</p>}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleEditCompany(company)}
                        className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteCompany(company.id)}
                        className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-4 lg:grid-cols-4">
                    <div className="rounded-2xl bg-slate-50 p-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Users</p>
                      <p className="mt-2 text-2xl font-black">{company.users_count}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Brands</p>
                      <p className="mt-2 text-2xl font-black">{company.brands_count}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Branches</p>
                      <p className="mt-2 text-2xl font-black">{company.branches_count}</p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">CEO</p>
                      <p className="mt-2 text-sm font-semibold text-slate-800">
                        {company.ceo ? `${company.ceo.first_name} ${company.ceo.last_name}` : 'Unassigned'}
                      </p>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <h4 className="text-lg font-bold text-slate-900">Brands</h4>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {company.brands.length > 0 ? (
                          company.brands.map((brand) => (
                            <span
                              key={brand.id}
                              className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700"
                            >
                              {brand.name}
                            </span>
                          ))
                        ) : (
                          <span className="text-sm text-slate-500">No brands assigned</span>
                        )}
                      </div>

                      <div className="mt-4 flex gap-2">
                        <input
                          value={brandDrafts[company.id] || ''}
                          onChange={(event) =>
                            setBrandDrafts((prev) => ({ ...prev, [company.id]: event.target.value }))
                          }
                          placeholder="Add brand name"
                          className="flex-1 rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 outline-none focus:border-indigo-500 focus:bg-white"
                        />
                        <button
                          type="button"
                          onClick={() => handleCreateBrand(company.id)}
                          disabled={submittingBrand[company.id]}
                          className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {submittingBrand[company.id] ? 'Adding...' : 'Add brand'}
                        </button>
                      </div>
                    </div>

                    <div>
                      <h4 className="mb-2 text-lg font-bold text-slate-900">CEO assignment</h4>
                      <div className="rounded-2xl bg-slate-50 p-3">
                        <div className="mb-3 text-sm text-slate-600">
                          {company.ceo ? (
                            <span>
                              Current CEO: <strong>{company.ceo.first_name} {company.ceo.last_name}</strong>
                            </span>
                          ) : (
                            'No CEO assigned yet'
                          )}
                        </div>

                        <div className="flex gap-2">
                          <select
                            id={`ceo-select-${company.id}`}
                            className="flex-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
                            defaultValue=""
                          >
                            <option value="">Select a user</option>
                            {systemUsers.map((userEntry) => (
                              <option key={userEntry.id} value={userEntry.id}>
                                {userEntry.first_name} {userEntry.last_name} ({userEntry.username})
                              </option>
                            ))}
                          </select>
                          <button
                            type="button"
                            onClick={() => handleAssignCeo(company.id)}
                            disabled={assigningCeo[company.id]}
                            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {assigningCeo[company.id] ? 'Saving...' : 'Assign'}
                          </button>
                        </div>

                        {company.ceo && (
                          <button
                            type="button"
                            onClick={() => handleRemoveCeo(company.id)}
                            className="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
                          >
                            Remove CEO
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
