package main
// https://docs.microsoft.com/zh-cn/windows/desktop/CIMWin32Prov/cim-wmi-provider
// https://blog.csdn.net/Cui_Cui_666/article/details/80507258
// https://blog.csdn.net/fyxichen/article/details/70230317

import (
	"encoding/json"
	"fmt"
	"net"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"
	"unsafe"

	"github.com/StackExchange/wmi"
	"github.com/jochasinga/requests"
)

var (
	kernel        = syscall.NewLazyDLL("Kernel32.dll")
	cmdb_host_api = "http://172.20.1.47:5001/api"
)

func main() {
	var hostname = GetHostName()
	var nic_info = getNetworkInfo(hostname)
	var cpu = int(runtime.NumCPU())
	var disk_total = 0
	var disk_info = GetDiskInfo()
	for _, v := range disk_info {
		// fmt.Printf("%T\n", v)
		disk_total += int(v.Total)
	}
	var mem = GetMemory()
	var os = runtime.GOOS
	// var os = GetOS()
	var manufacturer = GetVendor()
	var sn = GetSerialNumber()
	var uuid = GetUUID()

	//	fmt.Printf("主机名:%s\n", hostname)
	//	fmt.Printf("Interfaces:\t%s\n", nic_info)
	//	fmt.Printf("CPU:\t%T\n", cpu)
	//	fmt.Println(cpu)
	//	fmt.Printf("Disk:\t%d\n", disk_total/(1024*1024*1024))
	//	fmt.Printf("Memory:\t%s\n", mem)

	//	fmt.Printf("Manufacturer:%s\n", GetManufacturer())
	//	fmt.Printf("Product:%s\n", GetProduct())
	//	fmt.Printf("Vendor:%s\n", manufacturer)
	//	fmt.Printf("Vendor222:%s\n", GetVendor2())
	//	fmt.Printf("uuid:%s\n", uuid)
	//	fmt.Printf("sn:%s\n", sn)
	//	fmt.Printf("开机时长:%s\n", GetStartTime())
	//	fmt.Printf("当前用户:%s\n", GetUserName())
	//	fmt.Printf("当前系统:%s\n", os)
	//	fmt.Printf("系统版本:%s\n", GetSystemVersion())
	//	fmt.Printf("%s\n", GetBiosInfo())
	//	fmt.Printf("Motherboard:\t%s\n", GetMotherboardInfo())

	var server_info = make(map[string]string)
	server_info["hostname"] = hostname
	server_info["nic_mac_ip"] = nic_info
	server_info["server_cpu"] = strconv.Itoa(cpu)
	server_info["server_disk"] = strconv.Itoa(int(disk_total) / (1024 * 1024 * 1024))
	server_info["server_mem"] = mem
	server_info["manufacturer"] = manufacturer
	server_info["product_name"] = GetManufacturer()
	server_info["uuid"] = uuid
	server_info["sn"] = sn
	server_info["os"] = os
	server_info["status"] = "running"
	var vm_reg = regexp.MustCompile(`VMware|Virtual`)
	if vm_reg.MatchString(manufacturer) {
		server_info["is_vm"] = "1"
	} else {
		server_info["is_vm"] = "0"
	}
	
	fmt.Println(server_info)
	postData := map[string]interface{}{
		"id":      1,
		"jsonrpc": "2.0",
		"method":  "server.radd",
		"params":  server_info,
	}

	res, err := requests.PostJSON(cmdb_host_api, postData)
	if err != nil {
		fmt.Println(err)
	}
	fmt.Println(res.StatusCode)
	fmt.Println(res.String())

	//	req := HttpRequest.NewRequest()
	//	req.SetTimeout(5)
	//	req.Debug(true)
	//	req.SetHeaders(map[string]string{
	//		"Content-Type": "application/json",
	//	})
	//	postData := map[string]interface{}{
	//		"id":      1,
	//		"jsonrpc": "2.0",
	//		"method":  "server.radd",
	//		"params":  value_info,
	//	}
	//	resp, err := req.Post(cmdb_host_api, postData)

	//	if err != nil {
	//		fmt.Println(err)
	//		return
	//	}

	//	if resp.StatusCode() == 200 {
	//		body, err := resp.Body()

	//		if err != nil {
	//			fmt.Println(err)
	//			return
	//		}

	//		fmt.Println(string(body))
	//	} else {
	//		fmt.Println(resp.StatusCode())
	//	}
}

//开机时间
func GetStartTime() string {
	GetTickCount := kernel.NewProc("GetTickCount")
	r, _, _ := GetTickCount.Call()
	if r == 0 {
		return ""
	}
	ms := time.Duration(r * 1000 * 1000)
	return ms.String()
}

//当前用户名
func GetUserName() string {
	var size uint32 = 128
	var buffer = make([]uint16, size)
	user := syscall.StringToUTF16Ptr("USERNAME")
	domain := syscall.StringToUTF16Ptr("USERDOMAIN")
	r, err := syscall.GetEnvironmentVariable(user, &buffer[0], size)
	if err != nil {
		return ""
	}
	buffer[r] = '@'
	old := r + 1
	if old >= size {
		return syscall.UTF16ToString(buffer[:r])
	}
	r, err = syscall.GetEnvironmentVariable(domain, &buffer[old], size-old)
	return syscall.UTF16ToString(buffer[:old+r])
}

//系统版本
func GetSystemVersion() string {
	version, err := syscall.GetVersion()
	if err != nil {
		return ""
	}
	return fmt.Sprintf("%d.%d (%d)", byte(version), uint8(version>>8), version>>16)
}

type diskusage struct {
	Path  string `json:"path"`
	Total uint64 `json:"total"`
	Free  uint64 `json:"free"`
}

func usage(getDiskFreeSpaceExW *syscall.LazyProc, path string) (diskusage, error) {
	lpFreeBytesAvailable := int64(0)
	var info = diskusage{Path: path}
	diskret, _, err := getDiskFreeSpaceExW.Call(
		uintptr(unsafe.Pointer(syscall.StringToUTF16Ptr(info.Path))),
		uintptr(unsafe.Pointer(&lpFreeBytesAvailable)),
		uintptr(unsafe.Pointer(&(info.Total))),
		uintptr(unsafe.Pointer(&(info.Free))))
	if diskret != 0 {
		err = nil
	}
	return info, err
}

//硬盘信息
func GetDiskInfo() (infos []diskusage) {
	GetLogicalDriveStringsW := kernel.NewProc("GetLogicalDriveStringsW")
	GetDiskFreeSpaceExW := kernel.NewProc("GetDiskFreeSpaceExW")
	lpBuffer := make([]byte, 254)
	diskret, _, _ := GetLogicalDriveStringsW.Call(
		uintptr(len(lpBuffer)),
		uintptr(unsafe.Pointer(&lpBuffer[0])))
	if diskret == 0 {
		return
	}
	for _, v := range lpBuffer {
		if v >= 65 && v <= 90 {
			path := string(v) + ":"
			if path == "A:" || path == "B:" {
				continue
			}
			info, err := usage(GetDiskFreeSpaceExW, string(v)+":")
			if err != nil {
				continue
			}
			infos = append(infos, info)
		}
	}
	return infos
}

//CPU信息
//简单的获取方法fmt.Sprintf("Num:%d Arch:%s\n", runtime.NumCPU(), runtime.GOARCH)
func GetCpuInfo() string {
	var size uint32 = 128
	var buffer = make([]uint16, size)
	var index = uint32(copy(buffer, syscall.StringToUTF16("Num:")) - 1)
	nums := syscall.StringToUTF16Ptr("NUMBER_OF_PROCESSORS")
	arch := syscall.StringToUTF16Ptr("PROCESSOR_ARCHITECTURE")
	r, err := syscall.GetEnvironmentVariable(nums, &buffer[index], size-index)
	if err != nil {
		return ""
	}
	index += r
	index += uint32(copy(buffer[index:], syscall.StringToUTF16(" Arch:")) - 1)
	r, err = syscall.GetEnvironmentVariable(arch, &buffer[index], size-index)
	if err != nil {
		return syscall.UTF16ToString(buffer[:index])
	}
	index += r
	return syscall.UTF16ToString(buffer[:index+r])
}

type memoryStatusEx struct {
	cbSize                  uint32
	dwMemoryLoad            uint32
	ullTotalPhys            uint64 // in bytes
	ullAvailPhys            uint64
	ullTotalPageFile        uint64
	ullAvailPageFile        uint64
	ullTotalVirtual         uint64
	ullAvailVirtual         uint64
	ullAvailExtendedVirtual uint64
}

//内存信息
func GetMemory() string {
	GlobalMemoryStatusEx := kernel.NewProc("GlobalMemoryStatusEx")
	var memInfo memoryStatusEx
	memInfo.cbSize = uint32(unsafe.Sizeof(memInfo))
	mem, _, _ := GlobalMemoryStatusEx.Call(uintptr(unsafe.Pointer(&memInfo)))
	if mem == 0 {
		return ""
	}
	return fmt.Sprint(memInfo.ullTotalPhys / (1024 * 1024))
}

type Network struct {
	Name       string
	IP         string
	MACAddress string
}

type intfInfo struct {
	Name       string
	MacAddress string
	Ipv4       []string
}

func getNetworkInfo(hostname string) string {
	/*
			data = {
		        ["mac1"]:[
		            {"eth0": [ip1, ip2]},
		            {"eth0.1": [ip3]}
		            ],
		        ["mac2"]:...,
		    }
	*/
	intf, err := net.Interfaces()
	if err != nil {
		fmt.Println(err)
	}
	// var is = make([]intfInfo, len(intf))

	var data = make(map[string][]map[string][]string)

	var ip_reg = regexp.MustCompile(`^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$`)
	var dhcp_ip_reg = regexp.MustCompile(`^169\.254\.[0-9]{1,3}\.[0-9]{1,3}$`)
	var mac_reg = regexp.MustCompile(`^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$`)
	for _, v := range intf {
		ips, err := v.Addrs()
		if err != nil {
			fmt.Println(err)
		}
		//此处过滤loopback（本地回环）和isatap（isatap隧道）
		if !strings.Contains(v.Name, "Loopback") && !strings.Contains(v.Name, "isatap") {
			// var network Network
			// var intf_name = v.Name
			var intf_mac = v.HardwareAddr.String()
			// fmt.Println(intf_mac, mac_reg.MatchString(intf_mac))
			if mac_reg.MatchString(intf_mac) {
				var tmp_nic_ips = make(map[string][]string)
				for _, ip := range ips {
					var ip = strings.Split(ip.String(), "/")[0]
					// fmt.Println(ip)
					if dhcp_ip_reg.MatchString(ip) {
						continue
					}
					if ip_reg.MatchString(ip) {
						tmp_nic_ips[hostname] = append(tmp_nic_ips[hostname], ip)
						// is[i].Ipv4 = append(is[i].Ipv4, ip.String())
					}
				}
				data[intf_mac] = append(data[intf_mac], tmp_nic_ips)
			}
		}
	}
	b, err := json.Marshal(data)
	if err != nil {
		fmt.Println("json.Marshal failed:", err)
		return ""
	}
	return string(b)
}

//主板信息
func GetMotherboardInfo() string {
	type Win32_BaseBoard struct {
		Name    string
		Product string
		Model   string
	}

	var dst []Win32_BaseBoard
	err := wmi.Query("Select * from Win32_BaseBoard", &dst)
	if err != nil {
		return ""
	}
	for i, v := range dst {
		fmt.Printf("----", strconv.Itoa(i), v.Name, v.Product, v.Model)
	}
	return ""
}

//BIOS信息
func GetBiosInfo() string {
	var s = []struct {
		Name string
	}{}
	err := wmi.Query("SELECT Name FROM Win32_BIOS WHERE (Name IS NOT NULL)", &s) // WHERE (BIOSVersion IS NOT NULL)
	if err != nil {
		return ""
	}
	return s[0].Name
}

func GetHostName() string {
	var s = []struct {
		DNSHostName string
	}{}
	err := wmi.Query("SELECT DNSHostName FROM Win32_ComputerSystem", &s) // WHERE (BIOSVersion IS NOT NULL)
	if err != nil {
		return ""
	}
	return s[0].DNSHostName
}

func GetManufacturer() string {
	var s = []struct {
		Manufacturer string
	}{}
	err := wmi.Query("SELECT Manufacturer FROM Win32_ComputerSystem", &s) // WHERE (BIOSVersion IS NOT NULL)
	if err != nil {
		return ""
	}
	return s[0].Manufacturer
}

func GetVendor() string {
	var s = []struct {
		Model string
	}{}
	err := wmi.Query("SELECT Model FROM Win32_ComputerSystem", &s) // WHERE (BIOSVersion IS NOT NULL)
	if err != nil {
		return ""
	}
	return s[0].Model
}

func GetVendor2() string {
	var s = []struct {
		Vendor string
	}{}
	err := wmi.Query("SELECT Vendor FROM Win32_ComputerSystemProduct", &s) // WHERE (BIOSVersion IS NOT NULL)
	if err != nil {
		return ""
	}
	return s[0].Vendor
}

func GetSerialNumber() string {
	var s = []struct {
		IdentifyingNumber string
	}{}
	err := wmi.Query("SELECT IdentifyingNumber FROM Win32_ComputerSystemProduct", &s) // WHERE (BIOSVersion IS NOT NULL)
	if err != nil {
		return ""
	}
	return s[0].IdentifyingNumber
}

func GetProduct() string {
	var s = []struct {
		Product string
	}{}
	err := wmi.Query("SELECT Product FROM Win32_ComputerSystem", &s) // WHERE (BIOSVersion IS NOT NULL)
	if err != nil {
		return ""
	}
	return s[0].Product
}

type operatingSystem struct {
	Name    string
	Version string
}

func GetOS() string {
	var operatingsystem []operatingSystem
	err := wmi.Query("Select * from Win32_OperatingSystem", &operatingsystem)
	if err != nil {
		return ""
	}
	for _, os := range operatingsystem {
		fmt.Printf("OS info =%s\n", os.Name)
		fmt.Printf("OS info =%s\n", os.Version)
	}
	return ""
}

func GetUUID() string {
	var s = []struct {
		UUID string
	}{}
	err := wmi.Query("SELECT UUID FROM Win32_ComputerSystemProduct", &s) // WHERE (BIOSVersion IS NOT NULL)
	if err != nil {
		return ""
	}
	return s[0].UUID
}
