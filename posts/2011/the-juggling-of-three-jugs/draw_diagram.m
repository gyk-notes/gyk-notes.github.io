coord[0] = {0, 0};
coord[1] = {5, 0};
coord[2] = {2, 3};
coord[3] = {2, 0};
coord[4] = {0, 2};
coord[5] = {5, 2};
coord[6] = {4, 3};
coord[7] = {4, 0};
coord[Infinity] = {5, 3};

Do[coord[-i] = coord[Infinity] - coord[i], {i, 7}];

DrawIt[drawer_] := drawer[{coord[#1], coord[#2]}] &;

{MakeArrow, MakeLine} = {DrawIt[Arrow], DrawIt[Line]};

arrows = {MakeArrow[#, # + 1], MakeArrow[-#, -# - 1]} &  /@ 
   Range[0, 6];

lines = {MakeLine[-7, 7], MakeLine[1, Infinity], 
   MakeLine[-1, Infinity]};

MakeLabel[xy_, 
  t_] := {Text[
   Style[If[t < 0, IntegerString[-t] <> "'", t], 12,  
    FontFamily -> "Verdana"], xy, {-1.5, -1.5}]}

labels = MakeLabel[coord[#], #] & /@ (Range[-7, 7]~Append~ Infinity);

Show[Graphics[{arrows, Dashed, lines, labels, Orange, 
   PointSize[Large], Point[coord[7]]}]]

(****************)

DrawTiles[w_, 
  h_] := (DrawPointText[xy_, t_] := {PointSize[Large], Point[xy], 
    Black, Text[Style[t, Medium], xy, {-1.5, -1.5}]};
  half = LCM[w, h]/2;
  grids[interval_] := 
   Table[{i, Dashed}, {i, -half, half, 1}]~Join~
    Table[{i, {Orange, Thick}}, {i, -half, half, interval}];
  Show[Graphics[{Arrow[{{half, -half}, {-half, half}}], Pink, 
     DrawPointText[{0, 0}, C], Purple, DrawPointText[{1.5, -1.5}, P0],
      DrawPointText[{4.5, -4.5}, P1]}, 
    GridLines -> {grids[half*2/h], grids[half*2/w]}]])

DrawTiles[5, 3]
