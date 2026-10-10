# RPM Spec file for AI Reader
Name:           ai-reader
Version:        1.0.0
Release:        1%{?dist}
Summary:        Minimalist Cross-Platform AI Reader with NLP Knowledge Graph and MindMap
License:        MIT
URL:            https://github.com/ai-reader/ai-reader
Source0:        %{name}-%{version}.tar.gz

Requires:       gtk3 >= 3.24.0, glibc >= 2.31

%description
AI Reader is a Typora-style distraction-free reading application supporting EPUB,
PDF, Markdown, and TXT with offline classical NLP keyword extraction, co-occurrence
knowledge graphs, mind maps, and decoupled contextual AI annotations.

%prep
%setup -q

%build
# Pre-built release binaries copied in build script

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/usr/lib/ai-reader
mkdir -p $RPM_BUILD_ROOT/usr/share/applications

cp -r frontend/build/linux/x64/release/bundle/* $RPM_BUILD_ROOT/usr/lib/ai-reader/
cp backend/target/release/libreader_core.so $RPM_BUILD_ROOT/usr/lib/ai-reader/lib/
ln -sf /usr/lib/ai-reader/ai_reader $RPM_BUILD_ROOT/usr/bin/ai_reader
cp packaging/linux/deb/usr/share/applications/ai-reader.desktop $RPM_BUILD_ROOT/usr/share/applications/

%files
/usr/bin/ai_reader
/usr/lib/ai-reader/*
/usr/share/applications/ai-reader.desktop

%changelog
* Fri Oct 09 2026 AI Reader Team <dev@ai-reader.io> - 1.0.0-1
- Initial release with Typora-style reader, NLP graph, MindMap and decoupled AI margin annotations.
