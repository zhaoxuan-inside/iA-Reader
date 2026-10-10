Name:           ai-reader
Version:        2.0.0
Release:        1%{?dist}
Summary:        Editorial Minimalist AI Reader with iA Writer Margins & NLP Knowledge Graph

License:        MIT
URL:            https://github.com/ai-reader/ai-reader
Source0:        %{name}-%{version}.tar.gz

BuildArch:      x86_64
Requires:       python3, python3-gobject, gtk3

%description
AI Reader is a modern editorial reading workbench supporting EPUB, PDF,
Markdown, and TXT with iA Writer baseline-aligned marginalia, 4 deep cognitive
companion templates, offline classical NLP keyword extraction, co-occurrence
graphs, and structured interactive mind maps.

%prep
%setup -q

%build

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/usr/lib/ai-reader
mkdir -p $RPM_BUILD_ROOT/usr/share/applications
mkdir -p $RPM_BUILD_ROOT/usr/share/icons/hicolor/scalable/apps

install -m 755 linux/ai_reader_app.py $RPM_BUILD_ROOT/usr/lib/ai-reader/ai_reader
cp -r backend $RPM_BUILD_ROOT/usr/lib/ai-reader/
ln -sf /usr/lib/ai-reader/ai_reader $RPM_BUILD_ROOT/usr/bin/ai_reader

install -m 644 packaging/linux/deb/usr/share/applications/ai-reader.desktop $RPM_BUILD_ROOT/usr/share/applications/
install -m 644 packaging/linux/deb/usr/share/icons/hicolor/scalable/apps/ai-reader.svg $RPM_BUILD_ROOT/usr/share/icons/hicolor/scalable/apps/

%files
/usr/bin/ai_reader
/usr/lib/ai-reader
/usr/share/applications/ai-reader.desktop
/usr/share/icons/hicolor/scalable/apps/ai-reader.svg

%changelog
* Sat Oct 10 2026 AI Reader Team <dev@ai-reader.io> - 2.0.0-1
- Release v2.0.0 with Editorial typography, iA Writer marginalia, 4 cognitive templates, NLP graphs and mindmaps.
