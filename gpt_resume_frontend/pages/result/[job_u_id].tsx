import axios, { AxiosError, AxiosResponse } from "axios";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { Avatar } from "@/components/ui/avatar";
import { ApplicantDetailDialog } from "@/components/applicant-details-dialog";
import "../../styles/globals.css";
import { NavBar } from "@/components/nav-bar";

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";


export interface Applicant {
    u_id: string;
    name: string;
    email: string;
    resume: string;
    relevance: number;
}

interface ApplicantTableProps {
    applicants: Applicant[];
}




const getInitials = (fullName?: string) => {
  if (!fullName || fullName.trim().length === 0) return "";
  const parts = fullName.trim().split(" ").filter(Boolean);
  if (parts.length === 1) return parts[0][0]?.toUpperCase() ?? "";
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};



const ApplicantTable = (props: ApplicantTableProps) => {
    const applicants: Applicant[] = props.applicants;

    return (
        <div>
            <div><NavBar /></div>
            <Table>
                <TableHeader className="text-md bg-[#F9FAFB]">
                    <TableRow >
                        <TableHead className="grow">Name</TableHead>
                        <TableHead>Relevance Score</TableHead>
                        <TableHead>Resume Link</TableHead>
                        <TableHead></TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody className="overflow-y-scroll text-sm gap-0">
                    {applicants.map((applicant: Applicant) => (
                         
                         

                        <TableRow key={applicant.u_id || applicant.email} className="p-2 grow">
                            <TableCell className="flex gap-20 py-1 items-center">
                                <Avatar className="bg-[#F2F4F7] text-[#667085] font-semibold rounded-full my-auto text-center p-3 text-xs">
                                    
                                    {getInitials(applicant?.name)}


                                </Avatar>
                                <div className="flex flex-col justify-between">
                                    <p className="font-medium text-md">{applicant.name}</p>
                                    <p className="font-light text-gray-400 text-xs">{applicant.email}</p>
                                </div>
                            </TableCell>
                            <TableCell className="py-1 font-medium text-[#475467] text-sm">{applicant.relevance}</TableCell>
                            <TableCell className="text-[#5E5ADB] text-sm font-semibold py-1"><a href={`http://localhost:8000${applicant.resume}`} target="_blank">File</a></TableCell>
                            <TableCell className="text-right font-semibold text-[#475467] text-sm py-1">
                                <ApplicantDetailDialog u_id={applicant.u_id} name={applicant.name} email={applicant.email} resume={applicant.resume} relevance={applicant.relevance} />
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
                </Table>
            </div>
    );
};

export const ResultPage = () => {
    const router = useRouter();
    const { job_u_id } = router.query;
    const [recommendedProfiles, setRecommendedProfiles] = useState<Applicant[]>([]);
    const [notRecommendedProfiles, setNotRecommendedProfiles] = useState<Applicant[]>([]);


  useEffect(() => {
  if (!job_u_id) return;

  const jobId = Array.isArray(job_u_id) ? job_u_id[0] : job_u_id;

  axios.get(`http://localhost:8000/api/get-applicant-list/${jobId}/?type=rec`)
    .then((res: AxiosResponse) => {
      setRecommendedProfiles(res.data || []);
    })
    .catch((err: AxiosError) => console.error("Error fetching recommended:", err));

  axios.get(`http://localhost:8000/api/get-applicant-list/${jobId}/?type=norec`)
    .then((res: AxiosResponse) => {
      setNotRecommendedProfiles(res.data || []);
    })
    .catch((err: AxiosError) => console.error("Error fetching not recommended:", err));
}, [job_u_id]);



    return (
        <div className="w-full h-screen px-8 pt-6">
            <div className="w-full items-start h-fit border-b-2 pb-2">
                <h1 className="text-black font-bold text-2xl">
                    {recommendedProfiles.length} Resumes Filtered
                </h1>
                <p className="text-grey-500 font-light text-sm">
                    Purpose Selection
                </p>
            </div>
            <div className="flex mt-2 border-b-2 p-6">
                <div className="w-1/5">
                    <p className="font-bold text-lg">Recommended Profiles</p>
                    <p className="font-light text-[#475467] text-md">Resumes fit for the Job role</p>
                </div>
                <div className="w-4/5">
                    <ApplicantTable applicants={recommendedProfiles} />
                </div>
            </div>
            <div className="flex mt-2 p-6">
                <div className="w-1/5">
                    <p className="font-bold text-lg">Not Recommended Profiles</p>
                    <p className="font-light text-[#475467] text-md">Resumes not fit for the Job role</p>
                </div>
                <div className="w-4/5">
                    <ApplicantTable applicants={notRecommendedProfiles} />
                </div>
            </div>
        </div>
    );
};



export default ResultPage;
