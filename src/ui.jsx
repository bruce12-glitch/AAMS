/**
 * Single import surface for the console.
 * @astryxdesign/core has no Box and no Table.Header — wrap the real API here
 * so pages stay stable if the design kit moves.
 */
import React from 'react';
import {
  Theme,
  Layout,
  Stack,
  Grid,
  Card,
  Button,
  Badge,
  Table as AstryxTable,
  TableHeader,
  TableBody,
  TableRow,
  TableHeaderCell,
  TableCell,
  Text,
} from '@astryxdesign/core';
import { neutralTheme } from '@astryxdesign/theme-neutral';

export { Theme, Layout, Stack, Grid, Card, Button, Badge, Text, neutralTheme };

export function Box({ children, padding, marginTop, fontSize, fontWeight, style, ...rest }) {
  return (
    <div
      style={{
        padding: padding === 'md' ? 16 : padding === 'lg' ? 24 : padding === 'sm' ? 8 : padding,
        marginTop: marginTop === 'sm' ? 8 : marginTop === 'md' ? 16 : marginTop === 'lg' ? 24 : marginTop,
        fontSize,
        fontWeight,
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}

export function Table({ children }) {
  return <AstryxTable>{children}</AstryxTable>;
}
Table.Header = function Header({ children }) {
  return <TableHeader>{children}</TableHeader>;
};
Table.Body = function Body({ children }) {
  return <TableBody>{children}</TableBody>;
};
Table.Row = function Row({ children }) {
  return <TableRow>{children}</TableRow>;
};
Table.Head = function Head({ children }) {
  return <TableHeaderCell>{children}</TableHeaderCell>;
};
Table.Cell = function Cell({ children }) {
  return <TableCell>{children}</TableCell>;
};
