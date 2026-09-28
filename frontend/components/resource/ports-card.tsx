"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export type PortInfo = {
  name?: string;
  port: number | string;
  target_port: number | string;
  protocol: string;
};

type Props = {
  ports: PortInfo[];
};

export function PortsCard({
  ports,
}: Props) {

  return (

    <Card>

      <CardHeader>

        <CardTitle>
          Ports
        </CardTitle>

      </CardHeader>

      <CardContent>

        {ports.length === 0 ? (

          <div className="text-sm text-muted-foreground">
            No ports exposed.
          </div>

        ) : (

          <Table>

            <TableHeader>

              <TableRow>

                <TableHead>Name</TableHead>

                <TableHead>Port</TableHead>

                <TableHead>Target</TableHead>

                <TableHead>Protocol</TableHead>

              </TableRow>

            </TableHeader>

            <TableBody>

              {ports.map(
                (
                  port,
                  index,
                ) => (

                  <TableRow
                    key={index}
                  >

                    <TableCell>
                      {port.name || "-"}
                    </TableCell>

                    <TableCell>
                      {port.port}
                    </TableCell>

                    <TableCell>
                      {port.target_port}
                    </TableCell>

                    <TableCell>
                      {port.protocol}
                    </TableCell>

                  </TableRow>

                ),
              )}

            </TableBody>

          </Table>

        )}

      </CardContent>

    </Card>

  );

}