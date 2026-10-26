#!/usr/bin/env python3
"""Compare BTF FUNC names and struct layouts in two ARM64 kernel Images.
Usage: python3 research/compare_arm64_image_btf.py stock_boot.img r37_Image out_dir
Local-only; never writes a partition or creates a flashable image.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys

BTF = b"\x9f\xeb\x01\x00"

def payload(path):
    d = path.read_bytes()
    if d.startswith(b"ANDROID!"):
        size = struct.unpack_from("<I", d, 8)[0]
        version = struct.unpack_from("<I", d, 40)[0]
        if version not in (3,4) or size < 1000000 or size > len(d)-4096:
            raise ValueError("Unexpected Android boot v3/v4 header or invalid kernel_size")
        return d[4096:4096+size]
    return d

def read_btf(d):
    off = 0
    while True:
        off = d.find(BTF,off)
        if off<0:raise ValueError("No valid BTF found")
        orig=off
        off+=4
        if orig+24>len(d): continue
        _,_,_,hl,to,tl,so,sl = struct.unpack_from("<HBBIIIII",d,orig)
        if hl != 24 or tl<100000 or sl<100000 or orig+hl+max(to+tl,so+sl)>len(d):
            continue
        td=d[orig+hl+to:orig+hl+to+tl]
        sd=d[orig+hl+so:orig+hl+so+sl]
        def name(i):
            if i<0 or i>=len(sd): raise ValueError("Invalid BTF string offset")
            end=sd.find(b"\0",i)
            if end<0: raise ValueError("Unterminated BTF string")
            return sd[i:end].decode("utf-8","replace")
        funcs=set()
        structs={}
        p=0
        count=0
        try:
            while p<len(td):
                if p+12>len(td):raise ValueError("Incomplete BTF type")
                no,info,size=struct.unpack_from("<III",td,p)
                kind=(info>>24)&31
                vlen=info&65535
                flag=info>>31
                nm=name(no)
                extra={0:0,1:4,2:0,3:12,7:0,8:0,9:0,10:0,11:0,12:0,14:4,16:0,17:4,18:0}
                if kind == 12 and nm:funcs.add(nm)
                if kind in (4,5):
                    members=[]
                    for j in range(vlen):
                        mo,typ,offset=struct.unpack_from("<III",td,p+12+j*12)
                        members.append((name(mo),offset&0xffffff if flag else offset,offset>>24 if flag else 0))
                    if nm:structs.setdefault((kind,nm),[]).append((size,members))
                    step=12+12*vlen
                elif kind in (6,13):step=12+8*vlen
                elif kind in (15,19):step=12+12*vlen
                elif kind in extra:step=12+extra[kind]
                else:raise ValueError("Unknown BTF kind "+str(kind))
                p+=step
                count+=1
            if p!=len(td) or count<1000: raise ValueError("Invalid BTF boundaries")
            return {"funcs":funcs,"structs":structs,"type_count":count}
        except (ValueError,struct.error):
            continue

def main():
    if len(sys.argv)!=4:raise SystemExit(__doc__)
    stock_path, gki_path, out=map(Path,sys.argv[1:])
    out.mkdir(parents=True,exist_ok=True)
    raw_stock=payload(stock_path)
    raw_gki=payload(gki_path)
    a,b=read_btf(raw_stock),read_btf(raw_gki)
    only_stock=sorted(a["funcs"]-b["funcs"])
    only_gki=sorted(b["funcs"]-a["funcs"])
    changes=[]
    for key in sorted(a["structs"].keys() & b["structs"].keys()):
        sa,sb=a["structs"][key],b["structs"][key]
        if len(sa)!=1 or len(sb)!=1:continue
        (asz,am),(bsz,bm)=sa[0],sb[0]
        if asz==bsz and am==bm:continue
        ap={name:offset for name,offset,_ in am if name}
        bp={name:offset for name,offset,_ in bm if name}
        changes.append({"name":key[1],"kind":key[0],
                        "stock_bytes":asz,"gki_bytes":bsz,
                        "stock_only_members":sorted(ap.keys()-bp.keys()),
                        "gki_only_members":sorted(bp.keys()-ap.keys()),
                        "shifted_members":sorted(x for x in ap.keys()&bp.keys() if ap[x]!=bp[x])})
    # Common on-disk F2FS/EROFS layout names and separate DM runtime wrappers.
    # Compare names, bit offsets, bitfield sizes and sizeof, not BTF type IDs
    # (type IDs are local to each kernel build and cannot be compared directly).
    disk_names = ["f2fs_super_block", "f2fs_checkpoint", "f2fs_inode",
                  "f2fs_nat_block", "f2fs_node", "f2fs_summary_block",
                  "erofs_super_block"]
    dm_names = ["dm_target", "dm_dev"]
    disk_layout = []
    for name in disk_names + dm_names:
        key = (4, name)
        aa = a["structs"].get(key, [])
        bb = b["structs"].get(key, [])
        if len(aa) == 1 and len(bb) == 1:
            (asz, am), (bsz, bm) = aa[0], bb[0]
            disk_layout.append({
                "struct": name,
                "category": "on_disk" if name in disk_names else "device_mapper_runtime",
                "stock_size": asz,
                "gki_size": bsz,
                "stock_member_count": len(am),
                "gki_member_count": len(bm),
                "same_size_and_member_offsets": (asz == bsz and am == bm),
                "limitation": "Identical BTF layout cannot establish on-disk feature flags or runtime behavior"
            })
        else:
            disk_layout.append({"struct": name, "stock_records": len(aa),
                                "gki_records": len(bb), "comparison": "ambiguous"})
    report={
        "stock_kernel_sha256":hashlib.sha256(raw_stock).hexdigest(),
        "gki_kernel_sha256":hashlib.sha256(raw_gki).hexdigest(),
        "stock_btf_types":a["type_count"],"gki_btf_types":b["type_count"],
        "stock_btf_func_count":len(a["funcs"]),"gki_btf_func_count":len(b["funcs"]),
        "stock_only_funcs":only_stock,"gki_only_funcs":only_gki,
        "changed_struct_records":changes,
        "selected_storage_layouts":disk_layout,
        "safe_to_flash":False,
        "limitations":["BTF is not full System.map",
                       "BTF differences do not establish boot failure mechanism",
                       "Input stock boot must remain private and must not be uploaded to public CI"],
    }
    (out/"btf_diff.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    lines=["# Local-only BTF differences","",
           "Stock FUNC names: "+str(len(a["funcs"])),
           "GKI FUNC names: "+str(len(b["funcs"])),
           "Stock-only: "+str(len(only_stock)),
           "GKI-only: "+str(len(only_gki)),"",
           "## Stock-only BTF function names","",*only_stock,"",
           "## Changed struct layouts",
           "| Name | Stock bytes | GKI bytes | Shifted common members |",
           "|---|---:|---:|---:|"]
    lines += ["| "+x["name"]+" | "+str(x["stock_bytes"])+" | "+str(x["gki_bytes"])+
              " | "+str(len(x["shifted_members"]))+" |" for x in changes]
    lines += ["","## Selected storage/on-disk layouts","",
              "| Name | Class | Stock bytes | GKI bytes | Same member layout |",
              "|---|---|---:|---:|---|"]
    lines += ["| "+x["struct"]+" | "+x.get("category","unknown")+" | "+
              str(x.get("stock_size","?"))+" | "+str(x.get("gki_size","?"))+
              " | "+str(x.get("same_size_and_member_offsets","ambiguous"))+" |"
              for x in disk_layout]
    lines += ["","BTF equality does not establish equal on-disk feature-bit semantics.",
              "No flashable images are made by this tool.",""]
    (out/"README.md").write_text("\n".join(lines))
    print("Stock-only functions",len(only_stock),"r37-only functions",len(only_gki))
    print("Struct layouts changed",len(changes))
if __name__=="__main__":
    main()
