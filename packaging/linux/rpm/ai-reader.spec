Name:           ai-reader
Version:        0.0.1
Release:        1%{?dist}
Summary:        Headless Core Computation and Document Parsing Engine CLI

License:        MIT
URL:            https://github.com/ai-reader/ai-reader
Source0:        %{name}-%{version}.tar.gz

BuildArch:      x86_64
Requires:       python3

%description
AI Reader is a high-performance document parsing and cognitive computing engine
supporting EPUB, PDF, Markdown, and TXT with offline tri-level NLP keyword extraction,
concept co-occurrence topology graphs, structured mindmaps, SQLite persistence,
and cognitive companion pipelines.

%prep
%setup -q

%build

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/usr/lib/ai-reader

install -m 755 linux/ai_reader_app.py $RPM_BUILD_ROOT/usr/lib/ai-reader/ai_reader
cp -r backend $RPM_BUILD_ROOT/usr/lib/ai-reader/
ln -sf /usr/lib/ai-reader/ai_reader $RPM_BUILD_ROOT/usr/bin/ai_reader

%files
/usr/bin/ai_reader
/usr/lib/ai-reader

%changelog
* Sat Oct 10 2026 AI Reader Team <dev@ai-reader.io> - 3.0.0-1
- Release v3.0.0 headless core engine and CLI.
