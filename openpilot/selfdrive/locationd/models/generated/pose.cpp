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
void err_fun(double *nom_x, double *delta_x, double *out_7162235413577390203) {
   out_7162235413577390203[0] = delta_x[0] + nom_x[0];
   out_7162235413577390203[1] = delta_x[1] + nom_x[1];
   out_7162235413577390203[2] = delta_x[2] + nom_x[2];
   out_7162235413577390203[3] = delta_x[3] + nom_x[3];
   out_7162235413577390203[4] = delta_x[4] + nom_x[4];
   out_7162235413577390203[5] = delta_x[5] + nom_x[5];
   out_7162235413577390203[6] = delta_x[6] + nom_x[6];
   out_7162235413577390203[7] = delta_x[7] + nom_x[7];
   out_7162235413577390203[8] = delta_x[8] + nom_x[8];
   out_7162235413577390203[9] = delta_x[9] + nom_x[9];
   out_7162235413577390203[10] = delta_x[10] + nom_x[10];
   out_7162235413577390203[11] = delta_x[11] + nom_x[11];
   out_7162235413577390203[12] = delta_x[12] + nom_x[12];
   out_7162235413577390203[13] = delta_x[13] + nom_x[13];
   out_7162235413577390203[14] = delta_x[14] + nom_x[14];
   out_7162235413577390203[15] = delta_x[15] + nom_x[15];
   out_7162235413577390203[16] = delta_x[16] + nom_x[16];
   out_7162235413577390203[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7495913663529407299) {
   out_7495913663529407299[0] = -nom_x[0] + true_x[0];
   out_7495913663529407299[1] = -nom_x[1] + true_x[1];
   out_7495913663529407299[2] = -nom_x[2] + true_x[2];
   out_7495913663529407299[3] = -nom_x[3] + true_x[3];
   out_7495913663529407299[4] = -nom_x[4] + true_x[4];
   out_7495913663529407299[5] = -nom_x[5] + true_x[5];
   out_7495913663529407299[6] = -nom_x[6] + true_x[6];
   out_7495913663529407299[7] = -nom_x[7] + true_x[7];
   out_7495913663529407299[8] = -nom_x[8] + true_x[8];
   out_7495913663529407299[9] = -nom_x[9] + true_x[9];
   out_7495913663529407299[10] = -nom_x[10] + true_x[10];
   out_7495913663529407299[11] = -nom_x[11] + true_x[11];
   out_7495913663529407299[12] = -nom_x[12] + true_x[12];
   out_7495913663529407299[13] = -nom_x[13] + true_x[13];
   out_7495913663529407299[14] = -nom_x[14] + true_x[14];
   out_7495913663529407299[15] = -nom_x[15] + true_x[15];
   out_7495913663529407299[16] = -nom_x[16] + true_x[16];
   out_7495913663529407299[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_170725082104688702) {
   out_170725082104688702[0] = 1.0;
   out_170725082104688702[1] = 0.0;
   out_170725082104688702[2] = 0.0;
   out_170725082104688702[3] = 0.0;
   out_170725082104688702[4] = 0.0;
   out_170725082104688702[5] = 0.0;
   out_170725082104688702[6] = 0.0;
   out_170725082104688702[7] = 0.0;
   out_170725082104688702[8] = 0.0;
   out_170725082104688702[9] = 0.0;
   out_170725082104688702[10] = 0.0;
   out_170725082104688702[11] = 0.0;
   out_170725082104688702[12] = 0.0;
   out_170725082104688702[13] = 0.0;
   out_170725082104688702[14] = 0.0;
   out_170725082104688702[15] = 0.0;
   out_170725082104688702[16] = 0.0;
   out_170725082104688702[17] = 0.0;
   out_170725082104688702[18] = 0.0;
   out_170725082104688702[19] = 1.0;
   out_170725082104688702[20] = 0.0;
   out_170725082104688702[21] = 0.0;
   out_170725082104688702[22] = 0.0;
   out_170725082104688702[23] = 0.0;
   out_170725082104688702[24] = 0.0;
   out_170725082104688702[25] = 0.0;
   out_170725082104688702[26] = 0.0;
   out_170725082104688702[27] = 0.0;
   out_170725082104688702[28] = 0.0;
   out_170725082104688702[29] = 0.0;
   out_170725082104688702[30] = 0.0;
   out_170725082104688702[31] = 0.0;
   out_170725082104688702[32] = 0.0;
   out_170725082104688702[33] = 0.0;
   out_170725082104688702[34] = 0.0;
   out_170725082104688702[35] = 0.0;
   out_170725082104688702[36] = 0.0;
   out_170725082104688702[37] = 0.0;
   out_170725082104688702[38] = 1.0;
   out_170725082104688702[39] = 0.0;
   out_170725082104688702[40] = 0.0;
   out_170725082104688702[41] = 0.0;
   out_170725082104688702[42] = 0.0;
   out_170725082104688702[43] = 0.0;
   out_170725082104688702[44] = 0.0;
   out_170725082104688702[45] = 0.0;
   out_170725082104688702[46] = 0.0;
   out_170725082104688702[47] = 0.0;
   out_170725082104688702[48] = 0.0;
   out_170725082104688702[49] = 0.0;
   out_170725082104688702[50] = 0.0;
   out_170725082104688702[51] = 0.0;
   out_170725082104688702[52] = 0.0;
   out_170725082104688702[53] = 0.0;
   out_170725082104688702[54] = 0.0;
   out_170725082104688702[55] = 0.0;
   out_170725082104688702[56] = 0.0;
   out_170725082104688702[57] = 1.0;
   out_170725082104688702[58] = 0.0;
   out_170725082104688702[59] = 0.0;
   out_170725082104688702[60] = 0.0;
   out_170725082104688702[61] = 0.0;
   out_170725082104688702[62] = 0.0;
   out_170725082104688702[63] = 0.0;
   out_170725082104688702[64] = 0.0;
   out_170725082104688702[65] = 0.0;
   out_170725082104688702[66] = 0.0;
   out_170725082104688702[67] = 0.0;
   out_170725082104688702[68] = 0.0;
   out_170725082104688702[69] = 0.0;
   out_170725082104688702[70] = 0.0;
   out_170725082104688702[71] = 0.0;
   out_170725082104688702[72] = 0.0;
   out_170725082104688702[73] = 0.0;
   out_170725082104688702[74] = 0.0;
   out_170725082104688702[75] = 0.0;
   out_170725082104688702[76] = 1.0;
   out_170725082104688702[77] = 0.0;
   out_170725082104688702[78] = 0.0;
   out_170725082104688702[79] = 0.0;
   out_170725082104688702[80] = 0.0;
   out_170725082104688702[81] = 0.0;
   out_170725082104688702[82] = 0.0;
   out_170725082104688702[83] = 0.0;
   out_170725082104688702[84] = 0.0;
   out_170725082104688702[85] = 0.0;
   out_170725082104688702[86] = 0.0;
   out_170725082104688702[87] = 0.0;
   out_170725082104688702[88] = 0.0;
   out_170725082104688702[89] = 0.0;
   out_170725082104688702[90] = 0.0;
   out_170725082104688702[91] = 0.0;
   out_170725082104688702[92] = 0.0;
   out_170725082104688702[93] = 0.0;
   out_170725082104688702[94] = 0.0;
   out_170725082104688702[95] = 1.0;
   out_170725082104688702[96] = 0.0;
   out_170725082104688702[97] = 0.0;
   out_170725082104688702[98] = 0.0;
   out_170725082104688702[99] = 0.0;
   out_170725082104688702[100] = 0.0;
   out_170725082104688702[101] = 0.0;
   out_170725082104688702[102] = 0.0;
   out_170725082104688702[103] = 0.0;
   out_170725082104688702[104] = 0.0;
   out_170725082104688702[105] = 0.0;
   out_170725082104688702[106] = 0.0;
   out_170725082104688702[107] = 0.0;
   out_170725082104688702[108] = 0.0;
   out_170725082104688702[109] = 0.0;
   out_170725082104688702[110] = 0.0;
   out_170725082104688702[111] = 0.0;
   out_170725082104688702[112] = 0.0;
   out_170725082104688702[113] = 0.0;
   out_170725082104688702[114] = 1.0;
   out_170725082104688702[115] = 0.0;
   out_170725082104688702[116] = 0.0;
   out_170725082104688702[117] = 0.0;
   out_170725082104688702[118] = 0.0;
   out_170725082104688702[119] = 0.0;
   out_170725082104688702[120] = 0.0;
   out_170725082104688702[121] = 0.0;
   out_170725082104688702[122] = 0.0;
   out_170725082104688702[123] = 0.0;
   out_170725082104688702[124] = 0.0;
   out_170725082104688702[125] = 0.0;
   out_170725082104688702[126] = 0.0;
   out_170725082104688702[127] = 0.0;
   out_170725082104688702[128] = 0.0;
   out_170725082104688702[129] = 0.0;
   out_170725082104688702[130] = 0.0;
   out_170725082104688702[131] = 0.0;
   out_170725082104688702[132] = 0.0;
   out_170725082104688702[133] = 1.0;
   out_170725082104688702[134] = 0.0;
   out_170725082104688702[135] = 0.0;
   out_170725082104688702[136] = 0.0;
   out_170725082104688702[137] = 0.0;
   out_170725082104688702[138] = 0.0;
   out_170725082104688702[139] = 0.0;
   out_170725082104688702[140] = 0.0;
   out_170725082104688702[141] = 0.0;
   out_170725082104688702[142] = 0.0;
   out_170725082104688702[143] = 0.0;
   out_170725082104688702[144] = 0.0;
   out_170725082104688702[145] = 0.0;
   out_170725082104688702[146] = 0.0;
   out_170725082104688702[147] = 0.0;
   out_170725082104688702[148] = 0.0;
   out_170725082104688702[149] = 0.0;
   out_170725082104688702[150] = 0.0;
   out_170725082104688702[151] = 0.0;
   out_170725082104688702[152] = 1.0;
   out_170725082104688702[153] = 0.0;
   out_170725082104688702[154] = 0.0;
   out_170725082104688702[155] = 0.0;
   out_170725082104688702[156] = 0.0;
   out_170725082104688702[157] = 0.0;
   out_170725082104688702[158] = 0.0;
   out_170725082104688702[159] = 0.0;
   out_170725082104688702[160] = 0.0;
   out_170725082104688702[161] = 0.0;
   out_170725082104688702[162] = 0.0;
   out_170725082104688702[163] = 0.0;
   out_170725082104688702[164] = 0.0;
   out_170725082104688702[165] = 0.0;
   out_170725082104688702[166] = 0.0;
   out_170725082104688702[167] = 0.0;
   out_170725082104688702[168] = 0.0;
   out_170725082104688702[169] = 0.0;
   out_170725082104688702[170] = 0.0;
   out_170725082104688702[171] = 1.0;
   out_170725082104688702[172] = 0.0;
   out_170725082104688702[173] = 0.0;
   out_170725082104688702[174] = 0.0;
   out_170725082104688702[175] = 0.0;
   out_170725082104688702[176] = 0.0;
   out_170725082104688702[177] = 0.0;
   out_170725082104688702[178] = 0.0;
   out_170725082104688702[179] = 0.0;
   out_170725082104688702[180] = 0.0;
   out_170725082104688702[181] = 0.0;
   out_170725082104688702[182] = 0.0;
   out_170725082104688702[183] = 0.0;
   out_170725082104688702[184] = 0.0;
   out_170725082104688702[185] = 0.0;
   out_170725082104688702[186] = 0.0;
   out_170725082104688702[187] = 0.0;
   out_170725082104688702[188] = 0.0;
   out_170725082104688702[189] = 0.0;
   out_170725082104688702[190] = 1.0;
   out_170725082104688702[191] = 0.0;
   out_170725082104688702[192] = 0.0;
   out_170725082104688702[193] = 0.0;
   out_170725082104688702[194] = 0.0;
   out_170725082104688702[195] = 0.0;
   out_170725082104688702[196] = 0.0;
   out_170725082104688702[197] = 0.0;
   out_170725082104688702[198] = 0.0;
   out_170725082104688702[199] = 0.0;
   out_170725082104688702[200] = 0.0;
   out_170725082104688702[201] = 0.0;
   out_170725082104688702[202] = 0.0;
   out_170725082104688702[203] = 0.0;
   out_170725082104688702[204] = 0.0;
   out_170725082104688702[205] = 0.0;
   out_170725082104688702[206] = 0.0;
   out_170725082104688702[207] = 0.0;
   out_170725082104688702[208] = 0.0;
   out_170725082104688702[209] = 1.0;
   out_170725082104688702[210] = 0.0;
   out_170725082104688702[211] = 0.0;
   out_170725082104688702[212] = 0.0;
   out_170725082104688702[213] = 0.0;
   out_170725082104688702[214] = 0.0;
   out_170725082104688702[215] = 0.0;
   out_170725082104688702[216] = 0.0;
   out_170725082104688702[217] = 0.0;
   out_170725082104688702[218] = 0.0;
   out_170725082104688702[219] = 0.0;
   out_170725082104688702[220] = 0.0;
   out_170725082104688702[221] = 0.0;
   out_170725082104688702[222] = 0.0;
   out_170725082104688702[223] = 0.0;
   out_170725082104688702[224] = 0.0;
   out_170725082104688702[225] = 0.0;
   out_170725082104688702[226] = 0.0;
   out_170725082104688702[227] = 0.0;
   out_170725082104688702[228] = 1.0;
   out_170725082104688702[229] = 0.0;
   out_170725082104688702[230] = 0.0;
   out_170725082104688702[231] = 0.0;
   out_170725082104688702[232] = 0.0;
   out_170725082104688702[233] = 0.0;
   out_170725082104688702[234] = 0.0;
   out_170725082104688702[235] = 0.0;
   out_170725082104688702[236] = 0.0;
   out_170725082104688702[237] = 0.0;
   out_170725082104688702[238] = 0.0;
   out_170725082104688702[239] = 0.0;
   out_170725082104688702[240] = 0.0;
   out_170725082104688702[241] = 0.0;
   out_170725082104688702[242] = 0.0;
   out_170725082104688702[243] = 0.0;
   out_170725082104688702[244] = 0.0;
   out_170725082104688702[245] = 0.0;
   out_170725082104688702[246] = 0.0;
   out_170725082104688702[247] = 1.0;
   out_170725082104688702[248] = 0.0;
   out_170725082104688702[249] = 0.0;
   out_170725082104688702[250] = 0.0;
   out_170725082104688702[251] = 0.0;
   out_170725082104688702[252] = 0.0;
   out_170725082104688702[253] = 0.0;
   out_170725082104688702[254] = 0.0;
   out_170725082104688702[255] = 0.0;
   out_170725082104688702[256] = 0.0;
   out_170725082104688702[257] = 0.0;
   out_170725082104688702[258] = 0.0;
   out_170725082104688702[259] = 0.0;
   out_170725082104688702[260] = 0.0;
   out_170725082104688702[261] = 0.0;
   out_170725082104688702[262] = 0.0;
   out_170725082104688702[263] = 0.0;
   out_170725082104688702[264] = 0.0;
   out_170725082104688702[265] = 0.0;
   out_170725082104688702[266] = 1.0;
   out_170725082104688702[267] = 0.0;
   out_170725082104688702[268] = 0.0;
   out_170725082104688702[269] = 0.0;
   out_170725082104688702[270] = 0.0;
   out_170725082104688702[271] = 0.0;
   out_170725082104688702[272] = 0.0;
   out_170725082104688702[273] = 0.0;
   out_170725082104688702[274] = 0.0;
   out_170725082104688702[275] = 0.0;
   out_170725082104688702[276] = 0.0;
   out_170725082104688702[277] = 0.0;
   out_170725082104688702[278] = 0.0;
   out_170725082104688702[279] = 0.0;
   out_170725082104688702[280] = 0.0;
   out_170725082104688702[281] = 0.0;
   out_170725082104688702[282] = 0.0;
   out_170725082104688702[283] = 0.0;
   out_170725082104688702[284] = 0.0;
   out_170725082104688702[285] = 1.0;
   out_170725082104688702[286] = 0.0;
   out_170725082104688702[287] = 0.0;
   out_170725082104688702[288] = 0.0;
   out_170725082104688702[289] = 0.0;
   out_170725082104688702[290] = 0.0;
   out_170725082104688702[291] = 0.0;
   out_170725082104688702[292] = 0.0;
   out_170725082104688702[293] = 0.0;
   out_170725082104688702[294] = 0.0;
   out_170725082104688702[295] = 0.0;
   out_170725082104688702[296] = 0.0;
   out_170725082104688702[297] = 0.0;
   out_170725082104688702[298] = 0.0;
   out_170725082104688702[299] = 0.0;
   out_170725082104688702[300] = 0.0;
   out_170725082104688702[301] = 0.0;
   out_170725082104688702[302] = 0.0;
   out_170725082104688702[303] = 0.0;
   out_170725082104688702[304] = 1.0;
   out_170725082104688702[305] = 0.0;
   out_170725082104688702[306] = 0.0;
   out_170725082104688702[307] = 0.0;
   out_170725082104688702[308] = 0.0;
   out_170725082104688702[309] = 0.0;
   out_170725082104688702[310] = 0.0;
   out_170725082104688702[311] = 0.0;
   out_170725082104688702[312] = 0.0;
   out_170725082104688702[313] = 0.0;
   out_170725082104688702[314] = 0.0;
   out_170725082104688702[315] = 0.0;
   out_170725082104688702[316] = 0.0;
   out_170725082104688702[317] = 0.0;
   out_170725082104688702[318] = 0.0;
   out_170725082104688702[319] = 0.0;
   out_170725082104688702[320] = 0.0;
   out_170725082104688702[321] = 0.0;
   out_170725082104688702[322] = 0.0;
   out_170725082104688702[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_3543895396835097983) {
   out_3543895396835097983[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_3543895396835097983[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_3543895396835097983[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_3543895396835097983[3] = dt*state[12] + state[3];
   out_3543895396835097983[4] = dt*state[13] + state[4];
   out_3543895396835097983[5] = dt*state[14] + state[5];
   out_3543895396835097983[6] = state[6];
   out_3543895396835097983[7] = state[7];
   out_3543895396835097983[8] = state[8];
   out_3543895396835097983[9] = state[9];
   out_3543895396835097983[10] = state[10];
   out_3543895396835097983[11] = state[11];
   out_3543895396835097983[12] = state[12];
   out_3543895396835097983[13] = state[13];
   out_3543895396835097983[14] = state[14];
   out_3543895396835097983[15] = state[15];
   out_3543895396835097983[16] = state[16];
   out_3543895396835097983[17] = state[17];
}
void F_fun(double *state, double dt, double *out_585703334321150959) {
   out_585703334321150959[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_585703334321150959[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_585703334321150959[2] = 0;
   out_585703334321150959[3] = 0;
   out_585703334321150959[4] = 0;
   out_585703334321150959[5] = 0;
   out_585703334321150959[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_585703334321150959[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_585703334321150959[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_585703334321150959[9] = 0;
   out_585703334321150959[10] = 0;
   out_585703334321150959[11] = 0;
   out_585703334321150959[12] = 0;
   out_585703334321150959[13] = 0;
   out_585703334321150959[14] = 0;
   out_585703334321150959[15] = 0;
   out_585703334321150959[16] = 0;
   out_585703334321150959[17] = 0;
   out_585703334321150959[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_585703334321150959[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_585703334321150959[20] = 0;
   out_585703334321150959[21] = 0;
   out_585703334321150959[22] = 0;
   out_585703334321150959[23] = 0;
   out_585703334321150959[24] = 0;
   out_585703334321150959[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_585703334321150959[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_585703334321150959[27] = 0;
   out_585703334321150959[28] = 0;
   out_585703334321150959[29] = 0;
   out_585703334321150959[30] = 0;
   out_585703334321150959[31] = 0;
   out_585703334321150959[32] = 0;
   out_585703334321150959[33] = 0;
   out_585703334321150959[34] = 0;
   out_585703334321150959[35] = 0;
   out_585703334321150959[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_585703334321150959[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_585703334321150959[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_585703334321150959[39] = 0;
   out_585703334321150959[40] = 0;
   out_585703334321150959[41] = 0;
   out_585703334321150959[42] = 0;
   out_585703334321150959[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_585703334321150959[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_585703334321150959[45] = 0;
   out_585703334321150959[46] = 0;
   out_585703334321150959[47] = 0;
   out_585703334321150959[48] = 0;
   out_585703334321150959[49] = 0;
   out_585703334321150959[50] = 0;
   out_585703334321150959[51] = 0;
   out_585703334321150959[52] = 0;
   out_585703334321150959[53] = 0;
   out_585703334321150959[54] = 0;
   out_585703334321150959[55] = 0;
   out_585703334321150959[56] = 0;
   out_585703334321150959[57] = 1;
   out_585703334321150959[58] = 0;
   out_585703334321150959[59] = 0;
   out_585703334321150959[60] = 0;
   out_585703334321150959[61] = 0;
   out_585703334321150959[62] = 0;
   out_585703334321150959[63] = 0;
   out_585703334321150959[64] = 0;
   out_585703334321150959[65] = 0;
   out_585703334321150959[66] = dt;
   out_585703334321150959[67] = 0;
   out_585703334321150959[68] = 0;
   out_585703334321150959[69] = 0;
   out_585703334321150959[70] = 0;
   out_585703334321150959[71] = 0;
   out_585703334321150959[72] = 0;
   out_585703334321150959[73] = 0;
   out_585703334321150959[74] = 0;
   out_585703334321150959[75] = 0;
   out_585703334321150959[76] = 1;
   out_585703334321150959[77] = 0;
   out_585703334321150959[78] = 0;
   out_585703334321150959[79] = 0;
   out_585703334321150959[80] = 0;
   out_585703334321150959[81] = 0;
   out_585703334321150959[82] = 0;
   out_585703334321150959[83] = 0;
   out_585703334321150959[84] = 0;
   out_585703334321150959[85] = dt;
   out_585703334321150959[86] = 0;
   out_585703334321150959[87] = 0;
   out_585703334321150959[88] = 0;
   out_585703334321150959[89] = 0;
   out_585703334321150959[90] = 0;
   out_585703334321150959[91] = 0;
   out_585703334321150959[92] = 0;
   out_585703334321150959[93] = 0;
   out_585703334321150959[94] = 0;
   out_585703334321150959[95] = 1;
   out_585703334321150959[96] = 0;
   out_585703334321150959[97] = 0;
   out_585703334321150959[98] = 0;
   out_585703334321150959[99] = 0;
   out_585703334321150959[100] = 0;
   out_585703334321150959[101] = 0;
   out_585703334321150959[102] = 0;
   out_585703334321150959[103] = 0;
   out_585703334321150959[104] = dt;
   out_585703334321150959[105] = 0;
   out_585703334321150959[106] = 0;
   out_585703334321150959[107] = 0;
   out_585703334321150959[108] = 0;
   out_585703334321150959[109] = 0;
   out_585703334321150959[110] = 0;
   out_585703334321150959[111] = 0;
   out_585703334321150959[112] = 0;
   out_585703334321150959[113] = 0;
   out_585703334321150959[114] = 1;
   out_585703334321150959[115] = 0;
   out_585703334321150959[116] = 0;
   out_585703334321150959[117] = 0;
   out_585703334321150959[118] = 0;
   out_585703334321150959[119] = 0;
   out_585703334321150959[120] = 0;
   out_585703334321150959[121] = 0;
   out_585703334321150959[122] = 0;
   out_585703334321150959[123] = 0;
   out_585703334321150959[124] = 0;
   out_585703334321150959[125] = 0;
   out_585703334321150959[126] = 0;
   out_585703334321150959[127] = 0;
   out_585703334321150959[128] = 0;
   out_585703334321150959[129] = 0;
   out_585703334321150959[130] = 0;
   out_585703334321150959[131] = 0;
   out_585703334321150959[132] = 0;
   out_585703334321150959[133] = 1;
   out_585703334321150959[134] = 0;
   out_585703334321150959[135] = 0;
   out_585703334321150959[136] = 0;
   out_585703334321150959[137] = 0;
   out_585703334321150959[138] = 0;
   out_585703334321150959[139] = 0;
   out_585703334321150959[140] = 0;
   out_585703334321150959[141] = 0;
   out_585703334321150959[142] = 0;
   out_585703334321150959[143] = 0;
   out_585703334321150959[144] = 0;
   out_585703334321150959[145] = 0;
   out_585703334321150959[146] = 0;
   out_585703334321150959[147] = 0;
   out_585703334321150959[148] = 0;
   out_585703334321150959[149] = 0;
   out_585703334321150959[150] = 0;
   out_585703334321150959[151] = 0;
   out_585703334321150959[152] = 1;
   out_585703334321150959[153] = 0;
   out_585703334321150959[154] = 0;
   out_585703334321150959[155] = 0;
   out_585703334321150959[156] = 0;
   out_585703334321150959[157] = 0;
   out_585703334321150959[158] = 0;
   out_585703334321150959[159] = 0;
   out_585703334321150959[160] = 0;
   out_585703334321150959[161] = 0;
   out_585703334321150959[162] = 0;
   out_585703334321150959[163] = 0;
   out_585703334321150959[164] = 0;
   out_585703334321150959[165] = 0;
   out_585703334321150959[166] = 0;
   out_585703334321150959[167] = 0;
   out_585703334321150959[168] = 0;
   out_585703334321150959[169] = 0;
   out_585703334321150959[170] = 0;
   out_585703334321150959[171] = 1;
   out_585703334321150959[172] = 0;
   out_585703334321150959[173] = 0;
   out_585703334321150959[174] = 0;
   out_585703334321150959[175] = 0;
   out_585703334321150959[176] = 0;
   out_585703334321150959[177] = 0;
   out_585703334321150959[178] = 0;
   out_585703334321150959[179] = 0;
   out_585703334321150959[180] = 0;
   out_585703334321150959[181] = 0;
   out_585703334321150959[182] = 0;
   out_585703334321150959[183] = 0;
   out_585703334321150959[184] = 0;
   out_585703334321150959[185] = 0;
   out_585703334321150959[186] = 0;
   out_585703334321150959[187] = 0;
   out_585703334321150959[188] = 0;
   out_585703334321150959[189] = 0;
   out_585703334321150959[190] = 1;
   out_585703334321150959[191] = 0;
   out_585703334321150959[192] = 0;
   out_585703334321150959[193] = 0;
   out_585703334321150959[194] = 0;
   out_585703334321150959[195] = 0;
   out_585703334321150959[196] = 0;
   out_585703334321150959[197] = 0;
   out_585703334321150959[198] = 0;
   out_585703334321150959[199] = 0;
   out_585703334321150959[200] = 0;
   out_585703334321150959[201] = 0;
   out_585703334321150959[202] = 0;
   out_585703334321150959[203] = 0;
   out_585703334321150959[204] = 0;
   out_585703334321150959[205] = 0;
   out_585703334321150959[206] = 0;
   out_585703334321150959[207] = 0;
   out_585703334321150959[208] = 0;
   out_585703334321150959[209] = 1;
   out_585703334321150959[210] = 0;
   out_585703334321150959[211] = 0;
   out_585703334321150959[212] = 0;
   out_585703334321150959[213] = 0;
   out_585703334321150959[214] = 0;
   out_585703334321150959[215] = 0;
   out_585703334321150959[216] = 0;
   out_585703334321150959[217] = 0;
   out_585703334321150959[218] = 0;
   out_585703334321150959[219] = 0;
   out_585703334321150959[220] = 0;
   out_585703334321150959[221] = 0;
   out_585703334321150959[222] = 0;
   out_585703334321150959[223] = 0;
   out_585703334321150959[224] = 0;
   out_585703334321150959[225] = 0;
   out_585703334321150959[226] = 0;
   out_585703334321150959[227] = 0;
   out_585703334321150959[228] = 1;
   out_585703334321150959[229] = 0;
   out_585703334321150959[230] = 0;
   out_585703334321150959[231] = 0;
   out_585703334321150959[232] = 0;
   out_585703334321150959[233] = 0;
   out_585703334321150959[234] = 0;
   out_585703334321150959[235] = 0;
   out_585703334321150959[236] = 0;
   out_585703334321150959[237] = 0;
   out_585703334321150959[238] = 0;
   out_585703334321150959[239] = 0;
   out_585703334321150959[240] = 0;
   out_585703334321150959[241] = 0;
   out_585703334321150959[242] = 0;
   out_585703334321150959[243] = 0;
   out_585703334321150959[244] = 0;
   out_585703334321150959[245] = 0;
   out_585703334321150959[246] = 0;
   out_585703334321150959[247] = 1;
   out_585703334321150959[248] = 0;
   out_585703334321150959[249] = 0;
   out_585703334321150959[250] = 0;
   out_585703334321150959[251] = 0;
   out_585703334321150959[252] = 0;
   out_585703334321150959[253] = 0;
   out_585703334321150959[254] = 0;
   out_585703334321150959[255] = 0;
   out_585703334321150959[256] = 0;
   out_585703334321150959[257] = 0;
   out_585703334321150959[258] = 0;
   out_585703334321150959[259] = 0;
   out_585703334321150959[260] = 0;
   out_585703334321150959[261] = 0;
   out_585703334321150959[262] = 0;
   out_585703334321150959[263] = 0;
   out_585703334321150959[264] = 0;
   out_585703334321150959[265] = 0;
   out_585703334321150959[266] = 1;
   out_585703334321150959[267] = 0;
   out_585703334321150959[268] = 0;
   out_585703334321150959[269] = 0;
   out_585703334321150959[270] = 0;
   out_585703334321150959[271] = 0;
   out_585703334321150959[272] = 0;
   out_585703334321150959[273] = 0;
   out_585703334321150959[274] = 0;
   out_585703334321150959[275] = 0;
   out_585703334321150959[276] = 0;
   out_585703334321150959[277] = 0;
   out_585703334321150959[278] = 0;
   out_585703334321150959[279] = 0;
   out_585703334321150959[280] = 0;
   out_585703334321150959[281] = 0;
   out_585703334321150959[282] = 0;
   out_585703334321150959[283] = 0;
   out_585703334321150959[284] = 0;
   out_585703334321150959[285] = 1;
   out_585703334321150959[286] = 0;
   out_585703334321150959[287] = 0;
   out_585703334321150959[288] = 0;
   out_585703334321150959[289] = 0;
   out_585703334321150959[290] = 0;
   out_585703334321150959[291] = 0;
   out_585703334321150959[292] = 0;
   out_585703334321150959[293] = 0;
   out_585703334321150959[294] = 0;
   out_585703334321150959[295] = 0;
   out_585703334321150959[296] = 0;
   out_585703334321150959[297] = 0;
   out_585703334321150959[298] = 0;
   out_585703334321150959[299] = 0;
   out_585703334321150959[300] = 0;
   out_585703334321150959[301] = 0;
   out_585703334321150959[302] = 0;
   out_585703334321150959[303] = 0;
   out_585703334321150959[304] = 1;
   out_585703334321150959[305] = 0;
   out_585703334321150959[306] = 0;
   out_585703334321150959[307] = 0;
   out_585703334321150959[308] = 0;
   out_585703334321150959[309] = 0;
   out_585703334321150959[310] = 0;
   out_585703334321150959[311] = 0;
   out_585703334321150959[312] = 0;
   out_585703334321150959[313] = 0;
   out_585703334321150959[314] = 0;
   out_585703334321150959[315] = 0;
   out_585703334321150959[316] = 0;
   out_585703334321150959[317] = 0;
   out_585703334321150959[318] = 0;
   out_585703334321150959[319] = 0;
   out_585703334321150959[320] = 0;
   out_585703334321150959[321] = 0;
   out_585703334321150959[322] = 0;
   out_585703334321150959[323] = 1;
}
void h_4(double *state, double *unused, double *out_4198313265922725605) {
   out_4198313265922725605[0] = state[6] + state[9];
   out_4198313265922725605[1] = state[7] + state[10];
   out_4198313265922725605[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_924886084159401309) {
   out_924886084159401309[0] = 0;
   out_924886084159401309[1] = 0;
   out_924886084159401309[2] = 0;
   out_924886084159401309[3] = 0;
   out_924886084159401309[4] = 0;
   out_924886084159401309[5] = 0;
   out_924886084159401309[6] = 1;
   out_924886084159401309[7] = 0;
   out_924886084159401309[8] = 0;
   out_924886084159401309[9] = 1;
   out_924886084159401309[10] = 0;
   out_924886084159401309[11] = 0;
   out_924886084159401309[12] = 0;
   out_924886084159401309[13] = 0;
   out_924886084159401309[14] = 0;
   out_924886084159401309[15] = 0;
   out_924886084159401309[16] = 0;
   out_924886084159401309[17] = 0;
   out_924886084159401309[18] = 0;
   out_924886084159401309[19] = 0;
   out_924886084159401309[20] = 0;
   out_924886084159401309[21] = 0;
   out_924886084159401309[22] = 0;
   out_924886084159401309[23] = 0;
   out_924886084159401309[24] = 0;
   out_924886084159401309[25] = 1;
   out_924886084159401309[26] = 0;
   out_924886084159401309[27] = 0;
   out_924886084159401309[28] = 1;
   out_924886084159401309[29] = 0;
   out_924886084159401309[30] = 0;
   out_924886084159401309[31] = 0;
   out_924886084159401309[32] = 0;
   out_924886084159401309[33] = 0;
   out_924886084159401309[34] = 0;
   out_924886084159401309[35] = 0;
   out_924886084159401309[36] = 0;
   out_924886084159401309[37] = 0;
   out_924886084159401309[38] = 0;
   out_924886084159401309[39] = 0;
   out_924886084159401309[40] = 0;
   out_924886084159401309[41] = 0;
   out_924886084159401309[42] = 0;
   out_924886084159401309[43] = 0;
   out_924886084159401309[44] = 1;
   out_924886084159401309[45] = 0;
   out_924886084159401309[46] = 0;
   out_924886084159401309[47] = 1;
   out_924886084159401309[48] = 0;
   out_924886084159401309[49] = 0;
   out_924886084159401309[50] = 0;
   out_924886084159401309[51] = 0;
   out_924886084159401309[52] = 0;
   out_924886084159401309[53] = 0;
}
void h_10(double *state, double *unused, double *out_331605980695215593) {
   out_331605980695215593[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_331605980695215593[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_331605980695215593[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5486414686034992016) {
   out_5486414686034992016[0] = 0;
   out_5486414686034992016[1] = 9.8100000000000005*cos(state[1]);
   out_5486414686034992016[2] = 0;
   out_5486414686034992016[3] = 0;
   out_5486414686034992016[4] = -state[8];
   out_5486414686034992016[5] = state[7];
   out_5486414686034992016[6] = 0;
   out_5486414686034992016[7] = state[5];
   out_5486414686034992016[8] = -state[4];
   out_5486414686034992016[9] = 0;
   out_5486414686034992016[10] = 0;
   out_5486414686034992016[11] = 0;
   out_5486414686034992016[12] = 1;
   out_5486414686034992016[13] = 0;
   out_5486414686034992016[14] = 0;
   out_5486414686034992016[15] = 1;
   out_5486414686034992016[16] = 0;
   out_5486414686034992016[17] = 0;
   out_5486414686034992016[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5486414686034992016[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5486414686034992016[20] = 0;
   out_5486414686034992016[21] = state[8];
   out_5486414686034992016[22] = 0;
   out_5486414686034992016[23] = -state[6];
   out_5486414686034992016[24] = -state[5];
   out_5486414686034992016[25] = 0;
   out_5486414686034992016[26] = state[3];
   out_5486414686034992016[27] = 0;
   out_5486414686034992016[28] = 0;
   out_5486414686034992016[29] = 0;
   out_5486414686034992016[30] = 0;
   out_5486414686034992016[31] = 1;
   out_5486414686034992016[32] = 0;
   out_5486414686034992016[33] = 0;
   out_5486414686034992016[34] = 1;
   out_5486414686034992016[35] = 0;
   out_5486414686034992016[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5486414686034992016[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5486414686034992016[38] = 0;
   out_5486414686034992016[39] = -state[7];
   out_5486414686034992016[40] = state[6];
   out_5486414686034992016[41] = 0;
   out_5486414686034992016[42] = state[4];
   out_5486414686034992016[43] = -state[3];
   out_5486414686034992016[44] = 0;
   out_5486414686034992016[45] = 0;
   out_5486414686034992016[46] = 0;
   out_5486414686034992016[47] = 0;
   out_5486414686034992016[48] = 0;
   out_5486414686034992016[49] = 0;
   out_5486414686034992016[50] = 1;
   out_5486414686034992016[51] = 0;
   out_5486414686034992016[52] = 0;
   out_5486414686034992016[53] = 1;
}
void h_13(double *state, double *unused, double *out_6500207722279651616) {
   out_6500207722279651616[0] = state[3];
   out_6500207722279651616[1] = state[4];
   out_6500207722279651616[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4137159909491734110) {
   out_4137159909491734110[0] = 0;
   out_4137159909491734110[1] = 0;
   out_4137159909491734110[2] = 0;
   out_4137159909491734110[3] = 1;
   out_4137159909491734110[4] = 0;
   out_4137159909491734110[5] = 0;
   out_4137159909491734110[6] = 0;
   out_4137159909491734110[7] = 0;
   out_4137159909491734110[8] = 0;
   out_4137159909491734110[9] = 0;
   out_4137159909491734110[10] = 0;
   out_4137159909491734110[11] = 0;
   out_4137159909491734110[12] = 0;
   out_4137159909491734110[13] = 0;
   out_4137159909491734110[14] = 0;
   out_4137159909491734110[15] = 0;
   out_4137159909491734110[16] = 0;
   out_4137159909491734110[17] = 0;
   out_4137159909491734110[18] = 0;
   out_4137159909491734110[19] = 0;
   out_4137159909491734110[20] = 0;
   out_4137159909491734110[21] = 0;
   out_4137159909491734110[22] = 1;
   out_4137159909491734110[23] = 0;
   out_4137159909491734110[24] = 0;
   out_4137159909491734110[25] = 0;
   out_4137159909491734110[26] = 0;
   out_4137159909491734110[27] = 0;
   out_4137159909491734110[28] = 0;
   out_4137159909491734110[29] = 0;
   out_4137159909491734110[30] = 0;
   out_4137159909491734110[31] = 0;
   out_4137159909491734110[32] = 0;
   out_4137159909491734110[33] = 0;
   out_4137159909491734110[34] = 0;
   out_4137159909491734110[35] = 0;
   out_4137159909491734110[36] = 0;
   out_4137159909491734110[37] = 0;
   out_4137159909491734110[38] = 0;
   out_4137159909491734110[39] = 0;
   out_4137159909491734110[40] = 0;
   out_4137159909491734110[41] = 1;
   out_4137159909491734110[42] = 0;
   out_4137159909491734110[43] = 0;
   out_4137159909491734110[44] = 0;
   out_4137159909491734110[45] = 0;
   out_4137159909491734110[46] = 0;
   out_4137159909491734110[47] = 0;
   out_4137159909491734110[48] = 0;
   out_4137159909491734110[49] = 0;
   out_4137159909491734110[50] = 0;
   out_4137159909491734110[51] = 0;
   out_4137159909491734110[52] = 0;
   out_4137159909491734110[53] = 0;
}
void h_14(double *state, double *unused, double *out_4036957254120554746) {
   out_4036957254120554746[0] = state[6];
   out_4036957254120554746[1] = state[7];
   out_4036957254120554746[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4888126940498885838) {
   out_4888126940498885838[0] = 0;
   out_4888126940498885838[1] = 0;
   out_4888126940498885838[2] = 0;
   out_4888126940498885838[3] = 0;
   out_4888126940498885838[4] = 0;
   out_4888126940498885838[5] = 0;
   out_4888126940498885838[6] = 1;
   out_4888126940498885838[7] = 0;
   out_4888126940498885838[8] = 0;
   out_4888126940498885838[9] = 0;
   out_4888126940498885838[10] = 0;
   out_4888126940498885838[11] = 0;
   out_4888126940498885838[12] = 0;
   out_4888126940498885838[13] = 0;
   out_4888126940498885838[14] = 0;
   out_4888126940498885838[15] = 0;
   out_4888126940498885838[16] = 0;
   out_4888126940498885838[17] = 0;
   out_4888126940498885838[18] = 0;
   out_4888126940498885838[19] = 0;
   out_4888126940498885838[20] = 0;
   out_4888126940498885838[21] = 0;
   out_4888126940498885838[22] = 0;
   out_4888126940498885838[23] = 0;
   out_4888126940498885838[24] = 0;
   out_4888126940498885838[25] = 1;
   out_4888126940498885838[26] = 0;
   out_4888126940498885838[27] = 0;
   out_4888126940498885838[28] = 0;
   out_4888126940498885838[29] = 0;
   out_4888126940498885838[30] = 0;
   out_4888126940498885838[31] = 0;
   out_4888126940498885838[32] = 0;
   out_4888126940498885838[33] = 0;
   out_4888126940498885838[34] = 0;
   out_4888126940498885838[35] = 0;
   out_4888126940498885838[36] = 0;
   out_4888126940498885838[37] = 0;
   out_4888126940498885838[38] = 0;
   out_4888126940498885838[39] = 0;
   out_4888126940498885838[40] = 0;
   out_4888126940498885838[41] = 0;
   out_4888126940498885838[42] = 0;
   out_4888126940498885838[43] = 0;
   out_4888126940498885838[44] = 1;
   out_4888126940498885838[45] = 0;
   out_4888126940498885838[46] = 0;
   out_4888126940498885838[47] = 0;
   out_4888126940498885838[48] = 0;
   out_4888126940498885838[49] = 0;
   out_4888126940498885838[50] = 0;
   out_4888126940498885838[51] = 0;
   out_4888126940498885838[52] = 0;
   out_4888126940498885838[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_7162235413577390203) {
  err_fun(nom_x, delta_x, out_7162235413577390203);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7495913663529407299) {
  inv_err_fun(nom_x, true_x, out_7495913663529407299);
}
void pose_H_mod_fun(double *state, double *out_170725082104688702) {
  H_mod_fun(state, out_170725082104688702);
}
void pose_f_fun(double *state, double dt, double *out_3543895396835097983) {
  f_fun(state,  dt, out_3543895396835097983);
}
void pose_F_fun(double *state, double dt, double *out_585703334321150959) {
  F_fun(state,  dt, out_585703334321150959);
}
void pose_h_4(double *state, double *unused, double *out_4198313265922725605) {
  h_4(state, unused, out_4198313265922725605);
}
void pose_H_4(double *state, double *unused, double *out_924886084159401309) {
  H_4(state, unused, out_924886084159401309);
}
void pose_h_10(double *state, double *unused, double *out_331605980695215593) {
  h_10(state, unused, out_331605980695215593);
}
void pose_H_10(double *state, double *unused, double *out_5486414686034992016) {
  H_10(state, unused, out_5486414686034992016);
}
void pose_h_13(double *state, double *unused, double *out_6500207722279651616) {
  h_13(state, unused, out_6500207722279651616);
}
void pose_H_13(double *state, double *unused, double *out_4137159909491734110) {
  H_13(state, unused, out_4137159909491734110);
}
void pose_h_14(double *state, double *unused, double *out_4036957254120554746) {
  h_14(state, unused, out_4036957254120554746);
}
void pose_H_14(double *state, double *unused, double *out_4888126940498885838) {
  H_14(state, unused, out_4888126940498885838);
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
