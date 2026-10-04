#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_1501121085238419754) {
   out_1501121085238419754[0] = delta_x[0] + nom_x[0];
   out_1501121085238419754[1] = delta_x[1] + nom_x[1];
   out_1501121085238419754[2] = delta_x[2] + nom_x[2];
   out_1501121085238419754[3] = delta_x[3] + nom_x[3];
   out_1501121085238419754[4] = delta_x[4] + nom_x[4];
   out_1501121085238419754[5] = delta_x[5] + nom_x[5];
   out_1501121085238419754[6] = delta_x[6] + nom_x[6];
   out_1501121085238419754[7] = delta_x[7] + nom_x[7];
   out_1501121085238419754[8] = delta_x[8] + nom_x[8];
   out_1501121085238419754[9] = delta_x[9] + nom_x[9];
   out_1501121085238419754[10] = delta_x[10] + nom_x[10];
   out_1501121085238419754[11] = delta_x[11] + nom_x[11];
   out_1501121085238419754[12] = delta_x[12] + nom_x[12];
   out_1501121085238419754[13] = delta_x[13] + nom_x[13];
   out_1501121085238419754[14] = delta_x[14] + nom_x[14];
   out_1501121085238419754[15] = delta_x[15] + nom_x[15];
   out_1501121085238419754[16] = delta_x[16] + nom_x[16];
   out_1501121085238419754[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2556801483726826729) {
   out_2556801483726826729[0] = -nom_x[0] + true_x[0];
   out_2556801483726826729[1] = -nom_x[1] + true_x[1];
   out_2556801483726826729[2] = -nom_x[2] + true_x[2];
   out_2556801483726826729[3] = -nom_x[3] + true_x[3];
   out_2556801483726826729[4] = -nom_x[4] + true_x[4];
   out_2556801483726826729[5] = -nom_x[5] + true_x[5];
   out_2556801483726826729[6] = -nom_x[6] + true_x[6];
   out_2556801483726826729[7] = -nom_x[7] + true_x[7];
   out_2556801483726826729[8] = -nom_x[8] + true_x[8];
   out_2556801483726826729[9] = -nom_x[9] + true_x[9];
   out_2556801483726826729[10] = -nom_x[10] + true_x[10];
   out_2556801483726826729[11] = -nom_x[11] + true_x[11];
   out_2556801483726826729[12] = -nom_x[12] + true_x[12];
   out_2556801483726826729[13] = -nom_x[13] + true_x[13];
   out_2556801483726826729[14] = -nom_x[14] + true_x[14];
   out_2556801483726826729[15] = -nom_x[15] + true_x[15];
   out_2556801483726826729[16] = -nom_x[16] + true_x[16];
   out_2556801483726826729[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_839846666563197587) {
   out_839846666563197587[0] = 1.0;
   out_839846666563197587[1] = 0.0;
   out_839846666563197587[2] = 0.0;
   out_839846666563197587[3] = 0.0;
   out_839846666563197587[4] = 0.0;
   out_839846666563197587[5] = 0.0;
   out_839846666563197587[6] = 0.0;
   out_839846666563197587[7] = 0.0;
   out_839846666563197587[8] = 0.0;
   out_839846666563197587[9] = 0.0;
   out_839846666563197587[10] = 0.0;
   out_839846666563197587[11] = 0.0;
   out_839846666563197587[12] = 0.0;
   out_839846666563197587[13] = 0.0;
   out_839846666563197587[14] = 0.0;
   out_839846666563197587[15] = 0.0;
   out_839846666563197587[16] = 0.0;
   out_839846666563197587[17] = 0.0;
   out_839846666563197587[18] = 0.0;
   out_839846666563197587[19] = 1.0;
   out_839846666563197587[20] = 0.0;
   out_839846666563197587[21] = 0.0;
   out_839846666563197587[22] = 0.0;
   out_839846666563197587[23] = 0.0;
   out_839846666563197587[24] = 0.0;
   out_839846666563197587[25] = 0.0;
   out_839846666563197587[26] = 0.0;
   out_839846666563197587[27] = 0.0;
   out_839846666563197587[28] = 0.0;
   out_839846666563197587[29] = 0.0;
   out_839846666563197587[30] = 0.0;
   out_839846666563197587[31] = 0.0;
   out_839846666563197587[32] = 0.0;
   out_839846666563197587[33] = 0.0;
   out_839846666563197587[34] = 0.0;
   out_839846666563197587[35] = 0.0;
   out_839846666563197587[36] = 0.0;
   out_839846666563197587[37] = 0.0;
   out_839846666563197587[38] = 1.0;
   out_839846666563197587[39] = 0.0;
   out_839846666563197587[40] = 0.0;
   out_839846666563197587[41] = 0.0;
   out_839846666563197587[42] = 0.0;
   out_839846666563197587[43] = 0.0;
   out_839846666563197587[44] = 0.0;
   out_839846666563197587[45] = 0.0;
   out_839846666563197587[46] = 0.0;
   out_839846666563197587[47] = 0.0;
   out_839846666563197587[48] = 0.0;
   out_839846666563197587[49] = 0.0;
   out_839846666563197587[50] = 0.0;
   out_839846666563197587[51] = 0.0;
   out_839846666563197587[52] = 0.0;
   out_839846666563197587[53] = 0.0;
   out_839846666563197587[54] = 0.0;
   out_839846666563197587[55] = 0.0;
   out_839846666563197587[56] = 0.0;
   out_839846666563197587[57] = 1.0;
   out_839846666563197587[58] = 0.0;
   out_839846666563197587[59] = 0.0;
   out_839846666563197587[60] = 0.0;
   out_839846666563197587[61] = 0.0;
   out_839846666563197587[62] = 0.0;
   out_839846666563197587[63] = 0.0;
   out_839846666563197587[64] = 0.0;
   out_839846666563197587[65] = 0.0;
   out_839846666563197587[66] = 0.0;
   out_839846666563197587[67] = 0.0;
   out_839846666563197587[68] = 0.0;
   out_839846666563197587[69] = 0.0;
   out_839846666563197587[70] = 0.0;
   out_839846666563197587[71] = 0.0;
   out_839846666563197587[72] = 0.0;
   out_839846666563197587[73] = 0.0;
   out_839846666563197587[74] = 0.0;
   out_839846666563197587[75] = 0.0;
   out_839846666563197587[76] = 1.0;
   out_839846666563197587[77] = 0.0;
   out_839846666563197587[78] = 0.0;
   out_839846666563197587[79] = 0.0;
   out_839846666563197587[80] = 0.0;
   out_839846666563197587[81] = 0.0;
   out_839846666563197587[82] = 0.0;
   out_839846666563197587[83] = 0.0;
   out_839846666563197587[84] = 0.0;
   out_839846666563197587[85] = 0.0;
   out_839846666563197587[86] = 0.0;
   out_839846666563197587[87] = 0.0;
   out_839846666563197587[88] = 0.0;
   out_839846666563197587[89] = 0.0;
   out_839846666563197587[90] = 0.0;
   out_839846666563197587[91] = 0.0;
   out_839846666563197587[92] = 0.0;
   out_839846666563197587[93] = 0.0;
   out_839846666563197587[94] = 0.0;
   out_839846666563197587[95] = 1.0;
   out_839846666563197587[96] = 0.0;
   out_839846666563197587[97] = 0.0;
   out_839846666563197587[98] = 0.0;
   out_839846666563197587[99] = 0.0;
   out_839846666563197587[100] = 0.0;
   out_839846666563197587[101] = 0.0;
   out_839846666563197587[102] = 0.0;
   out_839846666563197587[103] = 0.0;
   out_839846666563197587[104] = 0.0;
   out_839846666563197587[105] = 0.0;
   out_839846666563197587[106] = 0.0;
   out_839846666563197587[107] = 0.0;
   out_839846666563197587[108] = 0.0;
   out_839846666563197587[109] = 0.0;
   out_839846666563197587[110] = 0.0;
   out_839846666563197587[111] = 0.0;
   out_839846666563197587[112] = 0.0;
   out_839846666563197587[113] = 0.0;
   out_839846666563197587[114] = 1.0;
   out_839846666563197587[115] = 0.0;
   out_839846666563197587[116] = 0.0;
   out_839846666563197587[117] = 0.0;
   out_839846666563197587[118] = 0.0;
   out_839846666563197587[119] = 0.0;
   out_839846666563197587[120] = 0.0;
   out_839846666563197587[121] = 0.0;
   out_839846666563197587[122] = 0.0;
   out_839846666563197587[123] = 0.0;
   out_839846666563197587[124] = 0.0;
   out_839846666563197587[125] = 0.0;
   out_839846666563197587[126] = 0.0;
   out_839846666563197587[127] = 0.0;
   out_839846666563197587[128] = 0.0;
   out_839846666563197587[129] = 0.0;
   out_839846666563197587[130] = 0.0;
   out_839846666563197587[131] = 0.0;
   out_839846666563197587[132] = 0.0;
   out_839846666563197587[133] = 1.0;
   out_839846666563197587[134] = 0.0;
   out_839846666563197587[135] = 0.0;
   out_839846666563197587[136] = 0.0;
   out_839846666563197587[137] = 0.0;
   out_839846666563197587[138] = 0.0;
   out_839846666563197587[139] = 0.0;
   out_839846666563197587[140] = 0.0;
   out_839846666563197587[141] = 0.0;
   out_839846666563197587[142] = 0.0;
   out_839846666563197587[143] = 0.0;
   out_839846666563197587[144] = 0.0;
   out_839846666563197587[145] = 0.0;
   out_839846666563197587[146] = 0.0;
   out_839846666563197587[147] = 0.0;
   out_839846666563197587[148] = 0.0;
   out_839846666563197587[149] = 0.0;
   out_839846666563197587[150] = 0.0;
   out_839846666563197587[151] = 0.0;
   out_839846666563197587[152] = 1.0;
   out_839846666563197587[153] = 0.0;
   out_839846666563197587[154] = 0.0;
   out_839846666563197587[155] = 0.0;
   out_839846666563197587[156] = 0.0;
   out_839846666563197587[157] = 0.0;
   out_839846666563197587[158] = 0.0;
   out_839846666563197587[159] = 0.0;
   out_839846666563197587[160] = 0.0;
   out_839846666563197587[161] = 0.0;
   out_839846666563197587[162] = 0.0;
   out_839846666563197587[163] = 0.0;
   out_839846666563197587[164] = 0.0;
   out_839846666563197587[165] = 0.0;
   out_839846666563197587[166] = 0.0;
   out_839846666563197587[167] = 0.0;
   out_839846666563197587[168] = 0.0;
   out_839846666563197587[169] = 0.0;
   out_839846666563197587[170] = 0.0;
   out_839846666563197587[171] = 1.0;
   out_839846666563197587[172] = 0.0;
   out_839846666563197587[173] = 0.0;
   out_839846666563197587[174] = 0.0;
   out_839846666563197587[175] = 0.0;
   out_839846666563197587[176] = 0.0;
   out_839846666563197587[177] = 0.0;
   out_839846666563197587[178] = 0.0;
   out_839846666563197587[179] = 0.0;
   out_839846666563197587[180] = 0.0;
   out_839846666563197587[181] = 0.0;
   out_839846666563197587[182] = 0.0;
   out_839846666563197587[183] = 0.0;
   out_839846666563197587[184] = 0.0;
   out_839846666563197587[185] = 0.0;
   out_839846666563197587[186] = 0.0;
   out_839846666563197587[187] = 0.0;
   out_839846666563197587[188] = 0.0;
   out_839846666563197587[189] = 0.0;
   out_839846666563197587[190] = 1.0;
   out_839846666563197587[191] = 0.0;
   out_839846666563197587[192] = 0.0;
   out_839846666563197587[193] = 0.0;
   out_839846666563197587[194] = 0.0;
   out_839846666563197587[195] = 0.0;
   out_839846666563197587[196] = 0.0;
   out_839846666563197587[197] = 0.0;
   out_839846666563197587[198] = 0.0;
   out_839846666563197587[199] = 0.0;
   out_839846666563197587[200] = 0.0;
   out_839846666563197587[201] = 0.0;
   out_839846666563197587[202] = 0.0;
   out_839846666563197587[203] = 0.0;
   out_839846666563197587[204] = 0.0;
   out_839846666563197587[205] = 0.0;
   out_839846666563197587[206] = 0.0;
   out_839846666563197587[207] = 0.0;
   out_839846666563197587[208] = 0.0;
   out_839846666563197587[209] = 1.0;
   out_839846666563197587[210] = 0.0;
   out_839846666563197587[211] = 0.0;
   out_839846666563197587[212] = 0.0;
   out_839846666563197587[213] = 0.0;
   out_839846666563197587[214] = 0.0;
   out_839846666563197587[215] = 0.0;
   out_839846666563197587[216] = 0.0;
   out_839846666563197587[217] = 0.0;
   out_839846666563197587[218] = 0.0;
   out_839846666563197587[219] = 0.0;
   out_839846666563197587[220] = 0.0;
   out_839846666563197587[221] = 0.0;
   out_839846666563197587[222] = 0.0;
   out_839846666563197587[223] = 0.0;
   out_839846666563197587[224] = 0.0;
   out_839846666563197587[225] = 0.0;
   out_839846666563197587[226] = 0.0;
   out_839846666563197587[227] = 0.0;
   out_839846666563197587[228] = 1.0;
   out_839846666563197587[229] = 0.0;
   out_839846666563197587[230] = 0.0;
   out_839846666563197587[231] = 0.0;
   out_839846666563197587[232] = 0.0;
   out_839846666563197587[233] = 0.0;
   out_839846666563197587[234] = 0.0;
   out_839846666563197587[235] = 0.0;
   out_839846666563197587[236] = 0.0;
   out_839846666563197587[237] = 0.0;
   out_839846666563197587[238] = 0.0;
   out_839846666563197587[239] = 0.0;
   out_839846666563197587[240] = 0.0;
   out_839846666563197587[241] = 0.0;
   out_839846666563197587[242] = 0.0;
   out_839846666563197587[243] = 0.0;
   out_839846666563197587[244] = 0.0;
   out_839846666563197587[245] = 0.0;
   out_839846666563197587[246] = 0.0;
   out_839846666563197587[247] = 1.0;
   out_839846666563197587[248] = 0.0;
   out_839846666563197587[249] = 0.0;
   out_839846666563197587[250] = 0.0;
   out_839846666563197587[251] = 0.0;
   out_839846666563197587[252] = 0.0;
   out_839846666563197587[253] = 0.0;
   out_839846666563197587[254] = 0.0;
   out_839846666563197587[255] = 0.0;
   out_839846666563197587[256] = 0.0;
   out_839846666563197587[257] = 0.0;
   out_839846666563197587[258] = 0.0;
   out_839846666563197587[259] = 0.0;
   out_839846666563197587[260] = 0.0;
   out_839846666563197587[261] = 0.0;
   out_839846666563197587[262] = 0.0;
   out_839846666563197587[263] = 0.0;
   out_839846666563197587[264] = 0.0;
   out_839846666563197587[265] = 0.0;
   out_839846666563197587[266] = 1.0;
   out_839846666563197587[267] = 0.0;
   out_839846666563197587[268] = 0.0;
   out_839846666563197587[269] = 0.0;
   out_839846666563197587[270] = 0.0;
   out_839846666563197587[271] = 0.0;
   out_839846666563197587[272] = 0.0;
   out_839846666563197587[273] = 0.0;
   out_839846666563197587[274] = 0.0;
   out_839846666563197587[275] = 0.0;
   out_839846666563197587[276] = 0.0;
   out_839846666563197587[277] = 0.0;
   out_839846666563197587[278] = 0.0;
   out_839846666563197587[279] = 0.0;
   out_839846666563197587[280] = 0.0;
   out_839846666563197587[281] = 0.0;
   out_839846666563197587[282] = 0.0;
   out_839846666563197587[283] = 0.0;
   out_839846666563197587[284] = 0.0;
   out_839846666563197587[285] = 1.0;
   out_839846666563197587[286] = 0.0;
   out_839846666563197587[287] = 0.0;
   out_839846666563197587[288] = 0.0;
   out_839846666563197587[289] = 0.0;
   out_839846666563197587[290] = 0.0;
   out_839846666563197587[291] = 0.0;
   out_839846666563197587[292] = 0.0;
   out_839846666563197587[293] = 0.0;
   out_839846666563197587[294] = 0.0;
   out_839846666563197587[295] = 0.0;
   out_839846666563197587[296] = 0.0;
   out_839846666563197587[297] = 0.0;
   out_839846666563197587[298] = 0.0;
   out_839846666563197587[299] = 0.0;
   out_839846666563197587[300] = 0.0;
   out_839846666563197587[301] = 0.0;
   out_839846666563197587[302] = 0.0;
   out_839846666563197587[303] = 0.0;
   out_839846666563197587[304] = 1.0;
   out_839846666563197587[305] = 0.0;
   out_839846666563197587[306] = 0.0;
   out_839846666563197587[307] = 0.0;
   out_839846666563197587[308] = 0.0;
   out_839846666563197587[309] = 0.0;
   out_839846666563197587[310] = 0.0;
   out_839846666563197587[311] = 0.0;
   out_839846666563197587[312] = 0.0;
   out_839846666563197587[313] = 0.0;
   out_839846666563197587[314] = 0.0;
   out_839846666563197587[315] = 0.0;
   out_839846666563197587[316] = 0.0;
   out_839846666563197587[317] = 0.0;
   out_839846666563197587[318] = 0.0;
   out_839846666563197587[319] = 0.0;
   out_839846666563197587[320] = 0.0;
   out_839846666563197587[321] = 0.0;
   out_839846666563197587[322] = 0.0;
   out_839846666563197587[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_4964874563314269219) {
   out_4964874563314269219[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_4964874563314269219[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_4964874563314269219[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_4964874563314269219[3] = dt*state[12] + state[3];
   out_4964874563314269219[4] = dt*state[13] + state[4];
   out_4964874563314269219[5] = dt*state[14] + state[5];
   out_4964874563314269219[6] = state[6];
   out_4964874563314269219[7] = state[7];
   out_4964874563314269219[8] = state[8];
   out_4964874563314269219[9] = state[9];
   out_4964874563314269219[10] = state[10];
   out_4964874563314269219[11] = state[11];
   out_4964874563314269219[12] = state[12];
   out_4964874563314269219[13] = state[13];
   out_4964874563314269219[14] = state[14];
   out_4964874563314269219[15] = state[15];
   out_4964874563314269219[16] = state[16];
   out_4964874563314269219[17] = state[17];
}
void F_fun(double *state, double dt, double *out_517376202194933410) {
   out_517376202194933410[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_517376202194933410[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_517376202194933410[2] = 0;
   out_517376202194933410[3] = 0;
   out_517376202194933410[4] = 0;
   out_517376202194933410[5] = 0;
   out_517376202194933410[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_517376202194933410[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_517376202194933410[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_517376202194933410[9] = 0;
   out_517376202194933410[10] = 0;
   out_517376202194933410[11] = 0;
   out_517376202194933410[12] = 0;
   out_517376202194933410[13] = 0;
   out_517376202194933410[14] = 0;
   out_517376202194933410[15] = 0;
   out_517376202194933410[16] = 0;
   out_517376202194933410[17] = 0;
   out_517376202194933410[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_517376202194933410[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_517376202194933410[20] = 0;
   out_517376202194933410[21] = 0;
   out_517376202194933410[22] = 0;
   out_517376202194933410[23] = 0;
   out_517376202194933410[24] = 0;
   out_517376202194933410[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_517376202194933410[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_517376202194933410[27] = 0;
   out_517376202194933410[28] = 0;
   out_517376202194933410[29] = 0;
   out_517376202194933410[30] = 0;
   out_517376202194933410[31] = 0;
   out_517376202194933410[32] = 0;
   out_517376202194933410[33] = 0;
   out_517376202194933410[34] = 0;
   out_517376202194933410[35] = 0;
   out_517376202194933410[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_517376202194933410[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_517376202194933410[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_517376202194933410[39] = 0;
   out_517376202194933410[40] = 0;
   out_517376202194933410[41] = 0;
   out_517376202194933410[42] = 0;
   out_517376202194933410[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_517376202194933410[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_517376202194933410[45] = 0;
   out_517376202194933410[46] = 0;
   out_517376202194933410[47] = 0;
   out_517376202194933410[48] = 0;
   out_517376202194933410[49] = 0;
   out_517376202194933410[50] = 0;
   out_517376202194933410[51] = 0;
   out_517376202194933410[52] = 0;
   out_517376202194933410[53] = 0;
   out_517376202194933410[54] = 0;
   out_517376202194933410[55] = 0;
   out_517376202194933410[56] = 0;
   out_517376202194933410[57] = 1;
   out_517376202194933410[58] = 0;
   out_517376202194933410[59] = 0;
   out_517376202194933410[60] = 0;
   out_517376202194933410[61] = 0;
   out_517376202194933410[62] = 0;
   out_517376202194933410[63] = 0;
   out_517376202194933410[64] = 0;
   out_517376202194933410[65] = 0;
   out_517376202194933410[66] = dt;
   out_517376202194933410[67] = 0;
   out_517376202194933410[68] = 0;
   out_517376202194933410[69] = 0;
   out_517376202194933410[70] = 0;
   out_517376202194933410[71] = 0;
   out_517376202194933410[72] = 0;
   out_517376202194933410[73] = 0;
   out_517376202194933410[74] = 0;
   out_517376202194933410[75] = 0;
   out_517376202194933410[76] = 1;
   out_517376202194933410[77] = 0;
   out_517376202194933410[78] = 0;
   out_517376202194933410[79] = 0;
   out_517376202194933410[80] = 0;
   out_517376202194933410[81] = 0;
   out_517376202194933410[82] = 0;
   out_517376202194933410[83] = 0;
   out_517376202194933410[84] = 0;
   out_517376202194933410[85] = dt;
   out_517376202194933410[86] = 0;
   out_517376202194933410[87] = 0;
   out_517376202194933410[88] = 0;
   out_517376202194933410[89] = 0;
   out_517376202194933410[90] = 0;
   out_517376202194933410[91] = 0;
   out_517376202194933410[92] = 0;
   out_517376202194933410[93] = 0;
   out_517376202194933410[94] = 0;
   out_517376202194933410[95] = 1;
   out_517376202194933410[96] = 0;
   out_517376202194933410[97] = 0;
   out_517376202194933410[98] = 0;
   out_517376202194933410[99] = 0;
   out_517376202194933410[100] = 0;
   out_517376202194933410[101] = 0;
   out_517376202194933410[102] = 0;
   out_517376202194933410[103] = 0;
   out_517376202194933410[104] = dt;
   out_517376202194933410[105] = 0;
   out_517376202194933410[106] = 0;
   out_517376202194933410[107] = 0;
   out_517376202194933410[108] = 0;
   out_517376202194933410[109] = 0;
   out_517376202194933410[110] = 0;
   out_517376202194933410[111] = 0;
   out_517376202194933410[112] = 0;
   out_517376202194933410[113] = 0;
   out_517376202194933410[114] = 1;
   out_517376202194933410[115] = 0;
   out_517376202194933410[116] = 0;
   out_517376202194933410[117] = 0;
   out_517376202194933410[118] = 0;
   out_517376202194933410[119] = 0;
   out_517376202194933410[120] = 0;
   out_517376202194933410[121] = 0;
   out_517376202194933410[122] = 0;
   out_517376202194933410[123] = 0;
   out_517376202194933410[124] = 0;
   out_517376202194933410[125] = 0;
   out_517376202194933410[126] = 0;
   out_517376202194933410[127] = 0;
   out_517376202194933410[128] = 0;
   out_517376202194933410[129] = 0;
   out_517376202194933410[130] = 0;
   out_517376202194933410[131] = 0;
   out_517376202194933410[132] = 0;
   out_517376202194933410[133] = 1;
   out_517376202194933410[134] = 0;
   out_517376202194933410[135] = 0;
   out_517376202194933410[136] = 0;
   out_517376202194933410[137] = 0;
   out_517376202194933410[138] = 0;
   out_517376202194933410[139] = 0;
   out_517376202194933410[140] = 0;
   out_517376202194933410[141] = 0;
   out_517376202194933410[142] = 0;
   out_517376202194933410[143] = 0;
   out_517376202194933410[144] = 0;
   out_517376202194933410[145] = 0;
   out_517376202194933410[146] = 0;
   out_517376202194933410[147] = 0;
   out_517376202194933410[148] = 0;
   out_517376202194933410[149] = 0;
   out_517376202194933410[150] = 0;
   out_517376202194933410[151] = 0;
   out_517376202194933410[152] = 1;
   out_517376202194933410[153] = 0;
   out_517376202194933410[154] = 0;
   out_517376202194933410[155] = 0;
   out_517376202194933410[156] = 0;
   out_517376202194933410[157] = 0;
   out_517376202194933410[158] = 0;
   out_517376202194933410[159] = 0;
   out_517376202194933410[160] = 0;
   out_517376202194933410[161] = 0;
   out_517376202194933410[162] = 0;
   out_517376202194933410[163] = 0;
   out_517376202194933410[164] = 0;
   out_517376202194933410[165] = 0;
   out_517376202194933410[166] = 0;
   out_517376202194933410[167] = 0;
   out_517376202194933410[168] = 0;
   out_517376202194933410[169] = 0;
   out_517376202194933410[170] = 0;
   out_517376202194933410[171] = 1;
   out_517376202194933410[172] = 0;
   out_517376202194933410[173] = 0;
   out_517376202194933410[174] = 0;
   out_517376202194933410[175] = 0;
   out_517376202194933410[176] = 0;
   out_517376202194933410[177] = 0;
   out_517376202194933410[178] = 0;
   out_517376202194933410[179] = 0;
   out_517376202194933410[180] = 0;
   out_517376202194933410[181] = 0;
   out_517376202194933410[182] = 0;
   out_517376202194933410[183] = 0;
   out_517376202194933410[184] = 0;
   out_517376202194933410[185] = 0;
   out_517376202194933410[186] = 0;
   out_517376202194933410[187] = 0;
   out_517376202194933410[188] = 0;
   out_517376202194933410[189] = 0;
   out_517376202194933410[190] = 1;
   out_517376202194933410[191] = 0;
   out_517376202194933410[192] = 0;
   out_517376202194933410[193] = 0;
   out_517376202194933410[194] = 0;
   out_517376202194933410[195] = 0;
   out_517376202194933410[196] = 0;
   out_517376202194933410[197] = 0;
   out_517376202194933410[198] = 0;
   out_517376202194933410[199] = 0;
   out_517376202194933410[200] = 0;
   out_517376202194933410[201] = 0;
   out_517376202194933410[202] = 0;
   out_517376202194933410[203] = 0;
   out_517376202194933410[204] = 0;
   out_517376202194933410[205] = 0;
   out_517376202194933410[206] = 0;
   out_517376202194933410[207] = 0;
   out_517376202194933410[208] = 0;
   out_517376202194933410[209] = 1;
   out_517376202194933410[210] = 0;
   out_517376202194933410[211] = 0;
   out_517376202194933410[212] = 0;
   out_517376202194933410[213] = 0;
   out_517376202194933410[214] = 0;
   out_517376202194933410[215] = 0;
   out_517376202194933410[216] = 0;
   out_517376202194933410[217] = 0;
   out_517376202194933410[218] = 0;
   out_517376202194933410[219] = 0;
   out_517376202194933410[220] = 0;
   out_517376202194933410[221] = 0;
   out_517376202194933410[222] = 0;
   out_517376202194933410[223] = 0;
   out_517376202194933410[224] = 0;
   out_517376202194933410[225] = 0;
   out_517376202194933410[226] = 0;
   out_517376202194933410[227] = 0;
   out_517376202194933410[228] = 1;
   out_517376202194933410[229] = 0;
   out_517376202194933410[230] = 0;
   out_517376202194933410[231] = 0;
   out_517376202194933410[232] = 0;
   out_517376202194933410[233] = 0;
   out_517376202194933410[234] = 0;
   out_517376202194933410[235] = 0;
   out_517376202194933410[236] = 0;
   out_517376202194933410[237] = 0;
   out_517376202194933410[238] = 0;
   out_517376202194933410[239] = 0;
   out_517376202194933410[240] = 0;
   out_517376202194933410[241] = 0;
   out_517376202194933410[242] = 0;
   out_517376202194933410[243] = 0;
   out_517376202194933410[244] = 0;
   out_517376202194933410[245] = 0;
   out_517376202194933410[246] = 0;
   out_517376202194933410[247] = 1;
   out_517376202194933410[248] = 0;
   out_517376202194933410[249] = 0;
   out_517376202194933410[250] = 0;
   out_517376202194933410[251] = 0;
   out_517376202194933410[252] = 0;
   out_517376202194933410[253] = 0;
   out_517376202194933410[254] = 0;
   out_517376202194933410[255] = 0;
   out_517376202194933410[256] = 0;
   out_517376202194933410[257] = 0;
   out_517376202194933410[258] = 0;
   out_517376202194933410[259] = 0;
   out_517376202194933410[260] = 0;
   out_517376202194933410[261] = 0;
   out_517376202194933410[262] = 0;
   out_517376202194933410[263] = 0;
   out_517376202194933410[264] = 0;
   out_517376202194933410[265] = 0;
   out_517376202194933410[266] = 1;
   out_517376202194933410[267] = 0;
   out_517376202194933410[268] = 0;
   out_517376202194933410[269] = 0;
   out_517376202194933410[270] = 0;
   out_517376202194933410[271] = 0;
   out_517376202194933410[272] = 0;
   out_517376202194933410[273] = 0;
   out_517376202194933410[274] = 0;
   out_517376202194933410[275] = 0;
   out_517376202194933410[276] = 0;
   out_517376202194933410[277] = 0;
   out_517376202194933410[278] = 0;
   out_517376202194933410[279] = 0;
   out_517376202194933410[280] = 0;
   out_517376202194933410[281] = 0;
   out_517376202194933410[282] = 0;
   out_517376202194933410[283] = 0;
   out_517376202194933410[284] = 0;
   out_517376202194933410[285] = 1;
   out_517376202194933410[286] = 0;
   out_517376202194933410[287] = 0;
   out_517376202194933410[288] = 0;
   out_517376202194933410[289] = 0;
   out_517376202194933410[290] = 0;
   out_517376202194933410[291] = 0;
   out_517376202194933410[292] = 0;
   out_517376202194933410[293] = 0;
   out_517376202194933410[294] = 0;
   out_517376202194933410[295] = 0;
   out_517376202194933410[296] = 0;
   out_517376202194933410[297] = 0;
   out_517376202194933410[298] = 0;
   out_517376202194933410[299] = 0;
   out_517376202194933410[300] = 0;
   out_517376202194933410[301] = 0;
   out_517376202194933410[302] = 0;
   out_517376202194933410[303] = 0;
   out_517376202194933410[304] = 1;
   out_517376202194933410[305] = 0;
   out_517376202194933410[306] = 0;
   out_517376202194933410[307] = 0;
   out_517376202194933410[308] = 0;
   out_517376202194933410[309] = 0;
   out_517376202194933410[310] = 0;
   out_517376202194933410[311] = 0;
   out_517376202194933410[312] = 0;
   out_517376202194933410[313] = 0;
   out_517376202194933410[314] = 0;
   out_517376202194933410[315] = 0;
   out_517376202194933410[316] = 0;
   out_517376202194933410[317] = 0;
   out_517376202194933410[318] = 0;
   out_517376202194933410[319] = 0;
   out_517376202194933410[320] = 0;
   out_517376202194933410[321] = 0;
   out_517376202194933410[322] = 0;
   out_517376202194933410[323] = 1;
}
void h_4(double *state, double *unused, double *out_1231289761953142672) {
   out_1231289761953142672[0] = state[6] + state[9];
   out_1231289761953142672[1] = state[7] + state[10];
   out_1231289761953142672[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_1417903479331939554) {
   out_1417903479331939554[0] = 0;
   out_1417903479331939554[1] = 0;
   out_1417903479331939554[2] = 0;
   out_1417903479331939554[3] = 0;
   out_1417903479331939554[4] = 0;
   out_1417903479331939554[5] = 0;
   out_1417903479331939554[6] = 1;
   out_1417903479331939554[7] = 0;
   out_1417903479331939554[8] = 0;
   out_1417903479331939554[9] = 1;
   out_1417903479331939554[10] = 0;
   out_1417903479331939554[11] = 0;
   out_1417903479331939554[12] = 0;
   out_1417903479331939554[13] = 0;
   out_1417903479331939554[14] = 0;
   out_1417903479331939554[15] = 0;
   out_1417903479331939554[16] = 0;
   out_1417903479331939554[17] = 0;
   out_1417903479331939554[18] = 0;
   out_1417903479331939554[19] = 0;
   out_1417903479331939554[20] = 0;
   out_1417903479331939554[21] = 0;
   out_1417903479331939554[22] = 0;
   out_1417903479331939554[23] = 0;
   out_1417903479331939554[24] = 0;
   out_1417903479331939554[25] = 1;
   out_1417903479331939554[26] = 0;
   out_1417903479331939554[27] = 0;
   out_1417903479331939554[28] = 1;
   out_1417903479331939554[29] = 0;
   out_1417903479331939554[30] = 0;
   out_1417903479331939554[31] = 0;
   out_1417903479331939554[32] = 0;
   out_1417903479331939554[33] = 0;
   out_1417903479331939554[34] = 0;
   out_1417903479331939554[35] = 0;
   out_1417903479331939554[36] = 0;
   out_1417903479331939554[37] = 0;
   out_1417903479331939554[38] = 0;
   out_1417903479331939554[39] = 0;
   out_1417903479331939554[40] = 0;
   out_1417903479331939554[41] = 0;
   out_1417903479331939554[42] = 0;
   out_1417903479331939554[43] = 0;
   out_1417903479331939554[44] = 1;
   out_1417903479331939554[45] = 0;
   out_1417903479331939554[46] = 0;
   out_1417903479331939554[47] = 1;
   out_1417903479331939554[48] = 0;
   out_1417903479331939554[49] = 0;
   out_1417903479331939554[50] = 0;
   out_1417903479331939554[51] = 0;
   out_1417903479331939554[52] = 0;
   out_1417903479331939554[53] = 0;
}
void h_10(double *state, double *unused, double *out_5694367547801407568) {
   out_5694367547801407568[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5694367547801407568[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5694367547801407568[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_412441903161159026) {
   out_412441903161159026[0] = 0;
   out_412441903161159026[1] = 9.8100000000000005*cos(state[1]);
   out_412441903161159026[2] = 0;
   out_412441903161159026[3] = 0;
   out_412441903161159026[4] = -state[8];
   out_412441903161159026[5] = state[7];
   out_412441903161159026[6] = 0;
   out_412441903161159026[7] = state[5];
   out_412441903161159026[8] = -state[4];
   out_412441903161159026[9] = 0;
   out_412441903161159026[10] = 0;
   out_412441903161159026[11] = 0;
   out_412441903161159026[12] = 1;
   out_412441903161159026[13] = 0;
   out_412441903161159026[14] = 0;
   out_412441903161159026[15] = 1;
   out_412441903161159026[16] = 0;
   out_412441903161159026[17] = 0;
   out_412441903161159026[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_412441903161159026[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_412441903161159026[20] = 0;
   out_412441903161159026[21] = state[8];
   out_412441903161159026[22] = 0;
   out_412441903161159026[23] = -state[6];
   out_412441903161159026[24] = -state[5];
   out_412441903161159026[25] = 0;
   out_412441903161159026[26] = state[3];
   out_412441903161159026[27] = 0;
   out_412441903161159026[28] = 0;
   out_412441903161159026[29] = 0;
   out_412441903161159026[30] = 0;
   out_412441903161159026[31] = 1;
   out_412441903161159026[32] = 0;
   out_412441903161159026[33] = 0;
   out_412441903161159026[34] = 1;
   out_412441903161159026[35] = 0;
   out_412441903161159026[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_412441903161159026[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_412441903161159026[38] = 0;
   out_412441903161159026[39] = -state[7];
   out_412441903161159026[40] = state[6];
   out_412441903161159026[41] = 0;
   out_412441903161159026[42] = state[4];
   out_412441903161159026[43] = -state[3];
   out_412441903161159026[44] = 0;
   out_412441903161159026[45] = 0;
   out_412441903161159026[46] = 0;
   out_412441903161159026[47] = 0;
   out_412441903161159026[48] = 0;
   out_412441903161159026[49] = 0;
   out_412441903161159026[50] = 1;
   out_412441903161159026[51] = 0;
   out_412441903161159026[52] = 0;
   out_412441903161159026[53] = 1;
}
void h_13(double *state, double *unused, double *out_3834866587183286615) {
   out_3834866587183286615[0] = state[3];
   out_3834866587183286615[1] = state[4];
   out_3834866587183286615[2] = state[5];
}
void H_13(double *state, double *unused, double *out_1794370346000393247) {
   out_1794370346000393247[0] = 0;
   out_1794370346000393247[1] = 0;
   out_1794370346000393247[2] = 0;
   out_1794370346000393247[3] = 1;
   out_1794370346000393247[4] = 0;
   out_1794370346000393247[5] = 0;
   out_1794370346000393247[6] = 0;
   out_1794370346000393247[7] = 0;
   out_1794370346000393247[8] = 0;
   out_1794370346000393247[9] = 0;
   out_1794370346000393247[10] = 0;
   out_1794370346000393247[11] = 0;
   out_1794370346000393247[12] = 0;
   out_1794370346000393247[13] = 0;
   out_1794370346000393247[14] = 0;
   out_1794370346000393247[15] = 0;
   out_1794370346000393247[16] = 0;
   out_1794370346000393247[17] = 0;
   out_1794370346000393247[18] = 0;
   out_1794370346000393247[19] = 0;
   out_1794370346000393247[20] = 0;
   out_1794370346000393247[21] = 0;
   out_1794370346000393247[22] = 1;
   out_1794370346000393247[23] = 0;
   out_1794370346000393247[24] = 0;
   out_1794370346000393247[25] = 0;
   out_1794370346000393247[26] = 0;
   out_1794370346000393247[27] = 0;
   out_1794370346000393247[28] = 0;
   out_1794370346000393247[29] = 0;
   out_1794370346000393247[30] = 0;
   out_1794370346000393247[31] = 0;
   out_1794370346000393247[32] = 0;
   out_1794370346000393247[33] = 0;
   out_1794370346000393247[34] = 0;
   out_1794370346000393247[35] = 0;
   out_1794370346000393247[36] = 0;
   out_1794370346000393247[37] = 0;
   out_1794370346000393247[38] = 0;
   out_1794370346000393247[39] = 0;
   out_1794370346000393247[40] = 0;
   out_1794370346000393247[41] = 1;
   out_1794370346000393247[42] = 0;
   out_1794370346000393247[43] = 0;
   out_1794370346000393247[44] = 0;
   out_1794370346000393247[45] = 0;
   out_1794370346000393247[46] = 0;
   out_1794370346000393247[47] = 0;
   out_1794370346000393247[48] = 0;
   out_1794370346000393247[49] = 0;
   out_1794370346000393247[50] = 0;
   out_1794370346000393247[51] = 0;
   out_1794370346000393247[52] = 0;
   out_1794370346000393247[53] = 0;
}
void h_14(double *state, double *unused, double *out_4481809147207636321) {
   out_4481809147207636321[0] = state[6];
   out_4481809147207636321[1] = state[7];
   out_4481809147207636321[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4500691911627311850) {
   out_4500691911627311850[0] = 0;
   out_4500691911627311850[1] = 0;
   out_4500691911627311850[2] = 0;
   out_4500691911627311850[3] = 0;
   out_4500691911627311850[4] = 0;
   out_4500691911627311850[5] = 0;
   out_4500691911627311850[6] = 1;
   out_4500691911627311850[7] = 0;
   out_4500691911627311850[8] = 0;
   out_4500691911627311850[9] = 0;
   out_4500691911627311850[10] = 0;
   out_4500691911627311850[11] = 0;
   out_4500691911627311850[12] = 0;
   out_4500691911627311850[13] = 0;
   out_4500691911627311850[14] = 0;
   out_4500691911627311850[15] = 0;
   out_4500691911627311850[16] = 0;
   out_4500691911627311850[17] = 0;
   out_4500691911627311850[18] = 0;
   out_4500691911627311850[19] = 0;
   out_4500691911627311850[20] = 0;
   out_4500691911627311850[21] = 0;
   out_4500691911627311850[22] = 0;
   out_4500691911627311850[23] = 0;
   out_4500691911627311850[24] = 0;
   out_4500691911627311850[25] = 1;
   out_4500691911627311850[26] = 0;
   out_4500691911627311850[27] = 0;
   out_4500691911627311850[28] = 0;
   out_4500691911627311850[29] = 0;
   out_4500691911627311850[30] = 0;
   out_4500691911627311850[31] = 0;
   out_4500691911627311850[32] = 0;
   out_4500691911627311850[33] = 0;
   out_4500691911627311850[34] = 0;
   out_4500691911627311850[35] = 0;
   out_4500691911627311850[36] = 0;
   out_4500691911627311850[37] = 0;
   out_4500691911627311850[38] = 0;
   out_4500691911627311850[39] = 0;
   out_4500691911627311850[40] = 0;
   out_4500691911627311850[41] = 0;
   out_4500691911627311850[42] = 0;
   out_4500691911627311850[43] = 0;
   out_4500691911627311850[44] = 1;
   out_4500691911627311850[45] = 0;
   out_4500691911627311850[46] = 0;
   out_4500691911627311850[47] = 0;
   out_4500691911627311850[48] = 0;
   out_4500691911627311850[49] = 0;
   out_4500691911627311850[50] = 0;
   out_4500691911627311850[51] = 0;
   out_4500691911627311850[52] = 0;
   out_4500691911627311850[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_1501121085238419754) {
  err_fun(nom_x, delta_x, out_1501121085238419754);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2556801483726826729) {
  inv_err_fun(nom_x, true_x, out_2556801483726826729);
}
void pose_H_mod_fun(double *state, double *out_839846666563197587) {
  H_mod_fun(state, out_839846666563197587);
}
void pose_f_fun(double *state, double dt, double *out_4964874563314269219) {
  f_fun(state,  dt, out_4964874563314269219);
}
void pose_F_fun(double *state, double dt, double *out_517376202194933410) {
  F_fun(state,  dt, out_517376202194933410);
}
void pose_h_4(double *state, double *unused, double *out_1231289761953142672) {
  h_4(state, unused, out_1231289761953142672);
}
void pose_H_4(double *state, double *unused, double *out_1417903479331939554) {
  H_4(state, unused, out_1417903479331939554);
}
void pose_h_10(double *state, double *unused, double *out_5694367547801407568) {
  h_10(state, unused, out_5694367547801407568);
}
void pose_H_10(double *state, double *unused, double *out_412441903161159026) {
  H_10(state, unused, out_412441903161159026);
}
void pose_h_13(double *state, double *unused, double *out_3834866587183286615) {
  h_13(state, unused, out_3834866587183286615);
}
void pose_H_13(double *state, double *unused, double *out_1794370346000393247) {
  H_13(state, unused, out_1794370346000393247);
}
void pose_h_14(double *state, double *unused, double *out_4481809147207636321) {
  h_14(state, unused, out_4481809147207636321);
}
void pose_H_14(double *state, double *unused, double *out_4500691911627311850) {
  H_14(state, unused, out_4500691911627311850);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
